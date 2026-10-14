# Telefonla stok sorgulama

Envanter → **Barkodla Stok Sorgula** (`/products/stock-lookup`). Yalnızca GET sorgulamasıdır; satış, stok hareketi veya muhasebe kaydı oluşturmaz. Mevcut giriş ve ürün erişim yetkisi gerekir. Fiyat ve stok sütunlarının mevcut yetkileri korunur; sonuçlar önbelleğe alınmaz.

Etiketteki tam birim barkodu, ortak barkod veya ürün kodu elle girilebilir. Kamera düğmesi yalnız kullanıcı istediğinde kamerayı açar; görüntü sunucuya yüklenmez. Okuma, kapatma, sayfadan ayrılma veya uygulamayı arka plana alma kamerayı durdurur.

Kamera için HTTPS ve Code 128 destekleyen BarcodeDetector API gerekir. Destek olmayan tarayıcıda (bazı iPhone/Safari sürümleri dahil) elle giriş kullanılmalıdır; tüm telefonlarda kamera desteği vaat edilmez. Kaynak: https://developer.mozilla.org/en-US/docs/Web/API/BarcodeDetector

Sonuç yalnız aktif mağazadaki ürün kaydına aittir. Aynı adlı ürünler veya farklı bedenler model/grup bağlantısı olmadan birleştirilmez. Satılmış birim etiketi ürünün kalan adedinden ayrı gösterilir.

Test kapsamı: tam barkod/ürün kodu, satılmış etiket, bilinmeyen giriş ve HTML kaçışları, mağaza izolasyonu, erişim/sütun yetkileri, sorgulama sonrası stok/satış/muhasebe sayılarının değişmemesi. JavaScript sözdizimi kontrol edilir. Fiziksel telefonda kamera/izin/okuma doğruluğu ve görsel kullanım ayrıca denenmelidir.
