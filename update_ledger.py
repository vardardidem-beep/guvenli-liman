#!/usr/bin/env python3
"""Güvenli Liman -- günlük bulut güncellemesi (Mac bağımsız).

HTML dosyasındaki <script type="application/json" id="ledger-state"> bloğunu
gerçek, canlı piyasa verileriyle günceller. HTML'in geri kalanı (CSS/JS/yapı)
HİÇ DEĞİŞTİRİLMEZ -- sadece bu bir JSON bloğu üzerine yazılır.

Kullanım: python3 update_ledger.py <html_dosya_yolu>
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

EFFECTIVE_SAFE_HAVEN_SPLIT = {
    "TL vadeli mevduat (TR bankası)": 0.18,
    "Kısa vadeli ABD Hazine bonosu ETF'i (örn. SGOV/BIL)": 0.18,
    "Stablecoin lending (Aave/Compound, itibarlı platform)": 0.18,
    "ETH staking (solo veya likit staking)": 0.15,
}
UNALLOCATED_PENDING = 0.31

RECOMMENDED_GROWTH_ALPHA_SPLIT = {
    "Geniş piyasa endeks fonu/ETF'i (örn. S&P 500)": 0.35,
    "Nasdaq-100 endeks fonu/ETF'i (örn. QQQ/QQQM)": 0.15,
    "Altın / kıymetli metaller (fiziksel veya ETF)": 0.20,
    "Gümüş (fiziksel, ETF veya TR banka/fon hesabı)": 0.10,
    "TR hisse senedi piyasası maruziyeti — BIST50 endeksi (bireysel hisse seçimi DEĞİL)": 0.10,
    "Bakır (ETF/emtia fonu — fiziksel TR banka hesabı YOK)": 0.05,
    "Uranyum (madenci hisseleri/ETF — fiziksel değil)": 0.05,
}
PROXY_TICKERS = {
    "Geniş piyasa endeks fonu/ETF'i (örn. S&P 500)": "SPY",
    "Nasdaq-100 endeks fonu/ETF'i (örn. QQQ/QQQM)": "QQQ",
    "Altın / kıymetli metaller (fiziksel veya ETF)": "GLD",
    "Gümüş (fiziksel, ETF veya TR banka/fon hesabı)": "SLV",
    "TR hisse senedi piyasası maruziyeti — BIST50 endeksi (bireysel hisse seçimi DEĞİL)": "ZELOT.IS",
    "Bakır (ETF/emtia fonu — fiziksel TR banka hesabı YOK)": "CPER",
    "Uranyum (madenci hisseleri/ETF — fiziksel değil)": "URA",
}
DEMO_TL_RATE_FALLBACK = 0.335
DEMO_ETH_STAKING_RATE_FALLBACK = 0.030
SGOV_APY_FALLBACK = 0.0361
MAX_GROWTH_ALPHA_SHARE_OF_TOTAL = 0.40
TRY_EXPOSURE_WARNING_THRESHOLD = 0.50


def fetch_price(ticker):
    req = urllib.request.Request(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    return data["chart"]["result"][0]["meta"]["regularMarketPrice"]


def fetch_stablecoin_apy():
    req = urllib.request.Request("https://yields.llama.fi/pools", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    vals, seen = [], set()
    for p in data["data"]:
        if p["chain"] == "Ethereum" and p["project"] in ("aave-v3", "compound-v3") and p["symbol"] in ("USDC", "USDT"):
            key = f'{p["project"]}_{p["symbol"]}'
            if key not in seen:
                seen.add(key)
                vals.append(p["apy"])
    return (sum(vals) / len(vals) / 100.0) if vals else 0.034


def main():
    html_path = sys.argv[1]
    with open(html_path, "r", encoding="utf-8") as fh:
        html = fh.read()

    m = re.search(r'(<script type="application/json" id="ledger-state">)(.*?)(</script>)', html, re.DOTALL)
    if not m:
        print("HATA: ledger-state script bloğu bulunamadı -- HTML beklenen şablonda değil", file=sys.stderr)
        sys.exit(1)
    prev_state = json.loads(m.group(2))

    now = datetime.now(timezone.utc)
    errors = {}

    # 1) Güvenli Liman günlük tahakkuk
    try:
        stablecoin_apy = fetch_stablecoin_apy()
    except Exception as e:
        errors["stablecoin_apy"] = f"{type(e).__name__}: {e}"
        stablecoin_apy = 0.034
    sgov_apy = SGOV_APY_FALLBACK

    principal = prev_state["safe_haven_principal"]
    daily_yield = 0.0
    for name, weight in EFFECTIVE_SAFE_HAVEN_SPLIT.items():
        amt = principal * weight
        if "TL" in name:
            apy = DEMO_TL_RATE_FALLBACK
        elif "Hazine" in name or "SGOV" in name:
            apy = sgov_apy
        elif "staking" in name:
            apy = DEMO_ETH_STAKING_RATE_FALLBACK
        else:
            apy = stablecoin_apy
        daily_yield += amt * apy / 365.0
    new_accrued = prev_state["safe_haven_accrued_unswept"] + daily_yield

    # 2) Büyüme/Alfa gerçek fiyat P&L
    prev_basis = prev_state.get("growth_alpha_price_basis", {})
    growth_balance = prev_state["growth_alpha_balance"]
    wsum = sum(RECOMMENDED_GROWTH_ALPHA_SPLIT.values())
    total_pnl = 0.0
    new_basis, pct_changes = {}, {}
    for name, ticker in PROXY_TICKERS.items():
        try:
            cur_price = fetch_price(ticker)
        except Exception as e:
            errors[name] = f"{type(e).__name__}: {e}"
            new_basis[name] = prev_basis.get(name, {"ticker": ticker, "last_price": None})
            pct_changes[name] = 0.0
            continue
        prev_price = (prev_basis.get(name) or {}).get("last_price")
        if prev_price:
            pct_change = (cur_price - prev_price) / prev_price
            notional = growth_balance * (RECOMMENDED_GROWTH_ALPHA_SPLIT[name] / wsum)
            total_pnl += notional * pct_change
            pct_changes[name] = round(pct_change * 100, 4)
        else:
            pct_changes[name] = 0.0
        new_basis[name] = {"ticker": ticker, "last_price": cur_price}
    new_growth_balance = growth_balance + total_pnl
    new_peak = max(prev_state.get("growth_alpha_peak_balance", 0.0), new_growth_balance)

    # 3) Risk göstergeleri
    total_system = principal + new_accrued + new_growth_balance
    drawdown_pct = 0.0
    if new_peak > 0:
        drawdown_pct = max(0.0, (new_peak - new_growth_balance) / new_peak) * 100
    share_pct = (new_growth_balance / total_system * 100) if total_system > 0 else 0.0

    # 4) TRY/USD maruziyeti
    safe_value = principal + new_accrued
    try_amt = safe_value * EFFECTIVE_SAFE_HAVEN_SPLIT["TL vadeli mevduat (TR bankası)"] + safe_value * UNALLOCATED_PENDING
    usd_cash_amt = safe_value * (
        EFFECTIVE_SAFE_HAVEN_SPLIT["Kısa vadeli ABD Hazine bonosu ETF'i (örn. SGOV/BIL)"]
        + EFFECTIVE_SAFE_HAVEN_SPLIT["Stablecoin lending (Aave/Compound, itibarlı platform)"]
    )
    usd_vol_amt = safe_value * EFFECTIVE_SAFE_HAVEN_SPLIT["ETH staking (solo veya likit staking)"] + new_growth_balance
    try_pct = (try_amt / total_system * 100) if total_system > 0 else 0.0
    usd_cash_pct = (usd_cash_amt / total_system * 100) if total_system > 0 else 0.0
    usd_vol_pct = (usd_vol_amt / total_system * 100) if total_system > 0 else 0.0

    # 5) Süreye göre getiri
    # started_at naive (tz'siz) olarak saklanıyor (two_tier_capital_structure.py ile
    # aynı konvansiyon) -- now'ı da naive'e çevirip karşılaştırıyoruz.
    started = datetime.fromisoformat(prev_state["started_at"])
    now_naive = now.replace(tzinfo=None)
    elapsed_days = max((now_naive - started).total_seconds() / 86400.0, 0.0)
    total_gain = new_accrued + new_growth_balance
    total_return_pct = (total_gain / principal * 100.0) if principal > 0 else 0.0

    # 6) Geçmiş (son 15 satır)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S")
    new_lines = [f"{ts} — Katman 1 kazancı tahakkuk etti: +{daily_yield:.2f}"]
    if abs(total_pnl) > 0.0001:
        new_lines.append(f"{ts} — Büyüme/Alfa gerçek piyasa {'kazancı' if total_pnl >= 0 else 'kaybı'}: {total_pnl:+.2f}")
    history = (prev_state.get("recent_history", []) + new_lines)[-15:]

    new_state = {
        "last_updated_utc": ts,
        "safe_haven_principal": principal,
        "safe_haven_accrued_unswept": new_accrued,
        "growth_alpha_balance": new_growth_balance,
        "growth_alpha_peak_balance": new_peak,
        "started_at": prev_state["started_at"],
        "total_return_pct": round(total_return_pct, 4),
        "effective_safe_haven_split": EFFECTIVE_SAFE_HAVEN_SPLIT,
        "unallocated_pending_rate_verification": UNALLOCATED_PENDING,
        "recommended_growth_alpha_split": RECOMMENDED_GROWTH_ALPHA_SPLIT,
        "growth_alpha_price_basis": new_basis,
        "last_price_pct_change": pct_changes,
        "growth_alpha_drawdown_pct": round(drawdown_pct, 2),
        "growth_alpha_share_pct": round(share_pct, 2),
        "growth_alpha_cap_pct": MAX_GROWTH_ALPHA_SHARE_OF_TOTAL * 100,
        "currency_exposure": {
            "try_pct": round(try_pct, 2),
            "usd_cash_like_pct": round(usd_cash_pct, 2),
            "usd_volatile_pct": round(usd_vol_pct, 2),
            "try_concentration_warning": (try_pct / 100) > TRY_EXPOSURE_WARNING_THRESHOLD,
        },
        "unverified_real_world_friction_items": prev_state["unverified_real_world_friction_items"],
        "recent_history": history,
        "_errors": errors,
    }

    new_json_text = json.dumps(new_state, indent=2, ensure_ascii=False)
    new_html = html[:m.start(2)] + "\n" + new_json_text + "\n" + html[m.end(2):]
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(new_html)

    print("OK")
    print(json.dumps({
        "total_return_pct": new_state["total_return_pct"],
        "growth_alpha_drawdown_pct": new_state["growth_alpha_drawdown_pct"],
        "growth_alpha_share_pct": new_state["growth_alpha_share_pct"],
        "errors": errors,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
