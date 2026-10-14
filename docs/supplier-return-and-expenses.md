# İade, fiyat önizlemesi ve gerçekleşen gider

- Finans → Toptancıya İade: her kayıt bir ürün/beden, bir veya birden çok adet. Birim barkod modunda her adet için tam barkod gerekir; ortak barkodda adet yeterlidir. Toptancı, ürün ve anlaşılan iade tutarı kullanıcı tarafından doğrulanır; yazılım ürünün bu toptancıdan alındığını kendiliğinden varsaymaz.
- Borçtan düş: yalnız seçilen toptancının aynı mağazadaki açık borcu azalır. Kasa hareketi oluşmaz. Borcu aşan tutar kabul edilmez; kalan kısım için uygun işlem ayrıca yapılır.
- Para iadesi: kullanıcı gerçekten aldığı nakit/banka iadesini kaydeder. Bankaya talimat gönderilmez, satış cirosu veya gider sayılmaz. Stok ve finans tek işlemde kaydedilir.
- İade geçmişi silinmez; aynı istek anahtarı ikinci stok/para hareketi üretmez. Mevcut genel ters kayıt ekranı bu bağlı iade işlemini iptal etmez. Yanlış iade düzeltmesi için ayrıca kontrollü akış gerekir.
- Cari ekranda ürün iadesiyle düşülen tutar, ödenen paradan ayrı gösterilir.
- Ürünler → seçili ürünler → toplu çarpan: çarpan seçildiğinde eski ve yeni KDV hariç fiyatlar gösterilir, onay gerekir. Eski satış fişleri değiştirilmez.
- Yeni ürün: beden bazlı adetler veya varyantsız stok miktarı × alış fiyatı gösterilir; bu önizleme kendiliğinden borç/ödeme oluşturmaz.
- Finans: planlanan giderli sonuç ve gerçekleşen giderli sonuç ayrıdır. Gerçek giderde onaylı genel gider hareketleri ve POS komisyonları, ters kayıtları düşülerek kullanılır. Tutarlar ödeme kayıtlarındaki KDV dâhil değerlerdir; yasal vergi kârı değildir. Tahakkuk etmiş ama henüz ödenmemiş giderler bu kutuya dahil olmaz.

## Yayın
Yeni `supplier_returns` tablosu eklenir; mevcut kayıtlar silinmez veya dönüştürülmez. Vercel WSGI açılışında yeni kurulum işaretiyle eklenir; diğer ortamlarda normal migration uygulanmalıdır. Canlıda test satışı/iadesi yapılmadı.

## Test stratejisi
Birim/entegrasyon: borç ve para iadesi, tekrar gönderim, yanlış barkod, fazla tutar/adet, mağaza izolasyonu, CSRF ve yetki sınırı, günlük gider ters kaydı, fiyat önizleme onayı. JavaScript davranış testi: farklı beden adetleri, + tuşu, varyantsız adet ve alış fiyatı değişimi. Tüm mevcut testler regresyon için çalıştırılır. PostgreSQL eşzamanlı istek/yayın kontrolü ve gerçek tarayıcı görsel kontrolü ayrıca canlıya geçişte doğrulanmalıdır.
