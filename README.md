# Güvenli Liman — kağıt üstü sermaye takip sistemi

**[DEMO — GERÇEK PARA DEĞİL.]** Bu, E10 (Iron Wall Capital) projesinin İki Katmanlı
Sermaye Yapısı'nın (Güvenli Liman + Büyüme/Alfa) kağıt üstü, canlı piyasa verisiyle
beslenen bir takip sistemidir. Hiçbir gerçek hesap, broker veya ödeme işlemi yapmaz —
sadece halka açık, ücretsiz piyasa verisi (Yahoo Finance chart API, DeFiLlama pools API)
okur ve `index.html` içindeki durumu günceller.

**Neden GitHub Actions?** Anthropic'in Claude Code bulut ortamı, güvenlik amacıyla
varsayılan-reddet bir ağ politikası kullanıyor — finans veri kaynaklarına (Yahoo
Finance, DeFiLlama, stooq.com dahil) erişim engelleniyor, ve bu organizasyon
politikasıyla kullanıcı tarafından da açılamıyor durumda (2026-08-23). GitHub
Actions'ın kendi runner'ları tam internet erişimine sahip, bu yüzden gerçek
otomasyon burada çalışıyor.

## Nasıl çalışır

1. `.github/workflows/daily-update.yml` her gün 06:00 UTC'de (09:00 İstanbul) çalışır.
2. `update_ledger.py`, `index.html` içindeki `<script type="application/json"
   id="ledger-state">` bloğunu okur, gerçek fiyatları çeker, günceller, geri yazar.
3. Değişiklik varsa otomatik commit + push edilir — bu da GitHub Pages'i yeniden
   deploy eder.
4. Sayfanın kendisi (`index.html`) tek başına, hiçbir dış bağımlılık olmadan açılır —
   embedded JSON'u okuyup görüntüler.

## Canlı sayfa

GitHub Pages ile yayınlanıyor: Settings → Pages → Source: `main` branch, `/ (root)`.

## Kullanım brief'i (Founder için)

**Canlı sayfa:** https://vardardidem-beep.github.io/guvenli-liman/
**Ne zaman güncellenir:** Otomatik, her gün 09:00 (İstanbul) — hiçbir şey yapman gerekmiyor.

### Üstteki 4 kutu — ilk bakılacak yer

| Kutu | Ne demek |
|---|---|
| **Toplam Sistem** | Anapara + kazanç + Alfa bakiyesi toplamı, ve altında demo başlangıcından beri toplam getiri % |
| **Anapara** | Dokunulmaz — asla azalmaz |
| **Süpürülmemiş Kazanç** | Katman 1'de biriken, henüz Alfa'ya aktarılmamış faiz |
| **Büyüme/Alfa** | Riskli katman bakiyesi + toplamın yüzde kaçını oluşturduğu (tavan %40) |

### Alttaki paneller

- **Güvenli Liman**: TL mevduat/SGOV/stablecoin/ETH staking arasındaki gerçek dağılım.
  "Teyit bekleyen pay" = henüz bankadan doğrulanmadığı için kazanç üretmeyen kısım.
- **Büyüme/Alfa**: 7 seçili enstrümanın (S&P500, Nasdaq, Altın, Gümüş, BIST50, Bakır,
  Uranyum) o günkü fiyat değişimi.
- **Döviz Maruziyeti**: TRY vs USD çubuğu — USD kendi içinde nakit-benzeri
  (SGOV/stablecoin) ve oynak (hisse/emtia) diye ayrılmış.
- **Gerçek-Sürtünme Kontrolü**: Gerçek paraya geçmeden önce bankadan/kurumdan teyit
  edilmesi gereken maddeler.

### Dikkat edilecek uyarılar

- ⚠ **Drawdown uyarısı**: Büyüme/Alfa tepe değerinin %30'undan fazlasını kaybettiyse çıkar.
- ⚠ **Pay tavanı**: Büyüme/Alfa %40'ı aşarsa çıkar (otomatik satış yapmaz, sadece uyarır).
- ⚠ **TRY yoğunlaşması**: Toplamın %50'sinden fazlası TL'ye bağlıysa çıkar.

### Bilmen gereken sınırlar

- **Hâlâ %100 kağıt üstü** — hiçbir gerçek hesap/para yok, "DEMO" rozeti bunu hatırlatıyor.
- Fiyatlar gerçek (Yahoo Finance/DeFiLlama), ama Büyüme/Alfa tarafında
  **enstrüman-bazlı gerçek pozisyon takibi yok** — sadece toplam bir bakiye, hedef
  ağırlıklarla yaklaşık dağıtılıyor (bkz. DECISION_REGISTER.md, 2026-08-23, KRİTİK
  bulgu — bilinçli olarak gerçek sermaye gelene kadar ertelendi).
- Gerçek sermaye koymadan önce "Gerçek-Sürtünme Kontrolü" listesindeki maddeler
  bankadan/kurumdan teyit edilmeli.

**Yapman gereken tek şey:** Ara sıra sayfaya bakmak. Sistem kendi kendine çalışıyor.

## Kaynak proje

Ana tasarım/kaynak: `E10 — Iron Wall Capital`, `PROTO_02_INTRADAY_NATIVE_ENGINE/
03_design/two_tier_capital_system/two_tier_capital_structure.py` — bu repo, o
projenin Mac-bağımsız, gerçekten 7/24 çalışan bir aynasıdır.
