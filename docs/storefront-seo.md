# Mağaza SEO düzenlemesi — 27 Ekim 2026

## Kapsam

Google için hedef: https://ihracfazlasigiyim.com üzerindeki ana sayfa, ürünler, kategoriler, hakkımızda ve SSS. Muhasebe/stok uygulaması, yönetim paneli, API, sepet ve favoriler arama sonuçlarına uygun içerik değildir. SEO düzenlemesi stok, fiyat, ödeme ve muhasebe kayıtlarını değiştirmez.

## Canlı başlangıç kontrolü

- Ana sayfa 200; canonical doğru mağaza alan adını gösteriyor.
- robots.txt 200; `/urunler?*` kuralı sayfalama bağlantılarını da engelliyor.
- sitemap.xml 200, 75 URL içeriyor. Bu kontrol indekslenme veya sıralama kanıtı değildir.
- Muhasebe uygulamasında `/login` 200; X-Robots-Tag başlığı bulunmuyor.
- Kodda VERCEL_URL, canonical alan adı seçilirken öncelikli. Geçici yayın adreslerinin esas adres olmasını engellemek için kaldırıldı.

## Uygulananlar

- Tek alan adı kaynağı: NEXT_PUBLIC_SITE_URL; tanımlı değilse gerçek mağaza alan adı. Robots, sitemap ve sayfa metadata bilgileri aynı kaynağı kullanır.
- Ürün listesi sayfalaması taranabilir. Filtreli sayfalar noindex/follow, sepet ve favoriler mevcut noindex ile kalır. Geçersiz sayfa numaraları normalize edilir.
- Flask yönetim uygulamasının tüm yanıtları noindex/nofollow/noarchive içerir. Next.js `/admin`, `/panel`, `/api` yanıtları için aynı başlık eklenir. Giriş kontrolü korunur. Noindex bir erişim yetkisi değildir; muhasebe yine girişle korunur.
- Ürün adı değiştiğinde eski adres, doğru ürün adresine kalıcı yönlenir. Metadata ve ürün sayfasındaki aynı veri isteği istek içinde paylaşılır.
- Ürün JSON-LD alanındaki ilk kelimeden marka tahmini kaldırılır. Fiyat, stok, ürün fotoğrafları ve SKU gerçek ürün verilerinden gelir. HTML içinde güvenli JSON serileştirilir.
- Sabit Google yorum sayısı LocalBusiness puan şemasından kaldırılır; görünür müşteri yorumları değiştirilmez. Puan/yorum sayılarının güncelliği ayrıca işletme tarafından doğrulanmalı.
- Var olmayan og-image.jpg yerine mevcut logo kullanılır. Ana sayfa başlığı sadeleştirilir.
- Üç ana kategoriye farklı, kullanıcıya yardımcı açıklamalar ve görünür sayfa yolu / BreadcrumbList eklenir.
- Sitemap bir saat arayla yenilenebilir; statik sayfalara her istekte sahte güncelleme tarihi yazılmaz. Ürünlerde gerçek updatedAt kullanılır. Veri hatasında eksik ürün listesi başarılı sitemap gibi sunulmaz.

## Doğrulama ve yayın sonrası

Yerelde TypeScript kontrolü, 6 SEO testi ve 9 giriş/güvenlik testi geçti. Tam üretim derlemesi, Google Rich Results Test ve Search Console URL denetimi bu çalışmada yapılmadı. Canlı veritabanında değişiklik yapılmadı. Yayına çıkmadan önce normal build kontrolü uygulanmalı.

Yayın sonrasında:
1. Yönetim girişinde ve panelde X-Robots-Tag başlığını; mağaza sayfalarında index/canonical değerlerini kontrol et.
2. Google Search Console'da yalnız mağaza alan adı için `/sitemap.xml` gönder; ana sayfa, bir kategori ve bir ürün için URL denetimi yap. Kodda doğrulama HTML dosyası bulunması Search Console erişiminin doğrulandığı anlamına gelmez.
3. Ürünü Rich Results Test ile kontrol et. Şemaya doğrulanmamış puan, marka, kargo veya iade vaadi ekleme.
4. Muhasebe URL'leri daha önce sonuçlara girdiyse noindex'in tekrar taranmasını bekle; acil gizleme için ilgili mülkün Search Console kaldırma aracını kullan. Özel uygulamanın URL'lerini mağaza sitemap'ine ekleme.
5. 2–4 hafta sonra mağaza URL'lerinin indekslenme durumu, gösterimleri ve tıklamalarını karşılaştır. Sıralama garantisi verilmez.

## Açık içerik işleri

Google puanı/yorum sayısı ve mağaza çalışma saatleri işletme tarafından güncel tutulmalı. Ürün açıklamalarına gerçek kumaş, kalıp ve ölçü bilgileri girilmeli; bunlar tahmin edilmedi. Footer'daki `/gizlilik` ve `/kullanim-sartlari` bağlantıları için yerel projede sayfa bulunamadı; gerçek politikalar hazırlanıp onaylandıktan sonra yayınlanmalı. İşletmenin Google Business Profile ve Search Console hesaplarına bu çalışma kapsamında giriş yapılmadı.

Kaynaklar:
- https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- https://developers.google.com/search/docs/appearance/structured-data/product-snippet
