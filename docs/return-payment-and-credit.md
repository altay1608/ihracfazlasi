# İade/değişim ödeme kontrolü

Yeni iade/değişimde ilk düğme **Farkı Kontrol Et** olur. Sunucu, geçmiş satış indirimleri ve KDV dahil tutar ile yeni ürün bedelini hesaplar. **Onayla ve Kaydet** öncesinde stok veya finans kaydı oluşturulmaz. Tutar, ürün, yöntem veya seçilen borç değişirse yeni önizleme gerekir; imza 10 dakika geçerlidir.

Nakit, Kredi Kartı, Havale/EFT yöntemleri seçilebilir. Bu yalnız muhasebe kaydıdır; bankaya veya fiziksel POS cihazına otomatik iade/tahsilat talimatı göndermez. Fiyat farkı yoksa yöntem zorunlu değildir. Kart komisyonu için ayrıca otomatik banka düzeltmesi yapılmaz.

Cari yetkisi olan kullanıcı tek bir açık borç seçebilir: iade edilen satışın veresiye borcu, aynı telefonla kayıtlı başka veresiye satış veya aynı telefonla kayıtlı müşteri cari alacağı. İsim benzerliği kullanılmaz. Fark pozitifse seçilen borç kadar mahsup edilir; kalan müşteriye seçilen yöntemle ödenir. Daha pahalı değişim ürününde fark tahsil edilir; bu akış yeni veresiye oluşturmaz. Birden çok borca dağıtım bu sürümde yoktur.

Mahsup nakit tahsilat olarak gösterilmez. Veresiye bakiyesi, ödeme ajandası ve cari kalan tutarı güncellenir. İşlem ve fiş üzerinde mahsup ile ödeme ayrı görünür. Mahsup uygulanmış hedef satışın mali düzenlemesi engellenir. Eski iade kayıtları geriye dönük değiştirilmez. Yeni `return_settlements` tablosu mevcut kayıtlar silinmeden migration/managed bootstrap ile eklenir. Diğer ortamlarda migration gerekir.

%110 kâr + KDV uyarısı yeni satıştan ve satış düzenlemeden kaldırılmıştır. Bu, fiyat/KDV hesaplama veya kâr raporu formüllerini değiştirmez.

## Test planı
Yerel geçici verilerle: önizlemenin veri değiştirmemesi, onay sonrası tek stok/kasa hareketi, eski finans eşitlemesinin ikinci kez işlememesi, veresiye mahsubunda kasanın değişmemesi, manuel cari ve aşan tutar, yanlış müşteri, değişen seçimde tekrar onay, tahsilat/iade/sıfır fark. Mevcut tüm testler regresyon için çalıştırılır. Gerçek PostgreSQL eşzamanlılık, canlı migration ve fiziksel POS iadesi bu testlere dahil değildir. İade işlemi için genel otomatik geri alma akışı eklenmemiştir.
