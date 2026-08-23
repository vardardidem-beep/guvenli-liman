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

## Kaynak proje

Ana tasarım/kaynak: `E10 — Iron Wall Capital`, `PROTO_02_INTRADAY_NATIVE_ENGINE/
03_design/two_tier_capital_system/two_tier_capital_structure.py` — bu repo, o
projenin Mac-bağımsız, gerçekten 7/24 çalışan bir aynasıdır.
