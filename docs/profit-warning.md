# Satış kâr eşiği uyarısı

Eşik: ürünün kayıtlı alış fiyatı × 2,10 × satışta kullanılan KDV çarpanı × adet.
Mevcut satış sistemi tüm normal satırlarda %10 KDV kullanır; bu geliştirme vergi oranını değiştirmez.
Sepet indirimi, satır indirimi sonrası normal satış tutarlarına oranlanır. Kuruş farkları en büyük kalan yöntemiyle dağıtılır.
Hediye ve şahsi kullanım hariçtir. Uyarı satış fiyatını değiştirmez; kullanıcı onayıyla devam edilir.
Onaysız istek stok rezervasyonu dahil geri alınır. Düzenlenen satışta da aynı kontrol yapılır.
Bu, maliyete eklenen %110 oranıdır; komisyon ve genel gider sonrası net kâr değildir.

## Test planı
- Birim: eşik eşitliği/1 kuruş altı, oranlı indirim, çoklu adet, sıfır fiyat, hediye/şahsi hariç tutma.
- Entegrasyon: onaysız satış ve güncellemede veritabanı/stok değişmemesi, onay sonrası tek satış.
- Regresyon: mevcut satış/KDV/fiş/muhasebe testlerinin tamamı ve JavaScript sözdizimi.
- Canlı verilerde deneme satışı yapılmaz. Gerçek tarayıcı/yazıcı onay akışı ayrıca kullanıcı kontrolü gerektirir.
