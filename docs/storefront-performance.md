# Mağaza yüklenme incelemesi — 27 Ekim 2026

Tek istemciden, tarayıcı dışında yapılan canlı HTTP ölçümü (Core Web Vitals testi değildir):

| Adres | İlk yanıt | Tüm yanıt | Sıkıştırma açıldıktan sonra boyut |
| --- | --- | --- | --- |
| Ana sayfa ilk istek | 976 ms | 1119 ms | 142492 bayt |
| Ana sayfa tekrar | 301 ms | 307 ms | 142492 bayt |
| /urunler | 2119 ms | 2522 ms | 136987 bayt |
| /kategori/ust-giyim | 1600 ms | 1764 ms | 206079 bayt |
| /hero-video.webm | 427 ms | 1822 ms | 4918993 bayt |

Ürün/kategori HTML yanıtları private/no-store. Kodda her istekte katalog veritabanı sorguları çalışıyor; kategori tüm ürünleri getiriyor. Ölçüm veritabanı, ağ ve sunucu süresini ayrı ayrı izole etmez; yalnız ilk yanıt gecikmesini kanıtlar. Ana sayfa önbellekli, ama 4,9 MB dekoratif video ek aktarım yükü oluşturuyor.

## Yerel iyileştirmeler

- Yalnız herkese açık ürün listesi ve kategori ürün sorgularına 15 saniyelik yeniden doğrulama aralığı olan Next veri önbelleği eklendi. Arama/beden/sıralama/sayfa ve kategori kimliği anahtarın parçası. Başarısız sorgu boş liste olarak önbelleğe kaydedilmez.
- Yeniden doğrulama arka planda olduğundan listelerde stok/fiyat güncellemesi hemen görünmeyebilir; 15 saniye kesin güncellik garantisi değildir. Ürün detayları, sipariş işlemleri ve yönetim sorgularına yeni bir önbellek eklenmedi. Yetkili oturum, muhasebe ve API yanıtları bu önbelleğe dahil değil.
- Ürün/kategori geçişlerine anında yükleniyor görünümü eklendi. Bu sunucu süresini azaltmaz; boş/bekleyen ekranı açıklığa kavuşturur.
- Ürün kartlarının kullanılmadan önce detay sayfalarını indirmesi kapatıldı; çok sayıda ürünün eşzamanlı sunucu isteği oluşturması azaltıldı.
- Mobil, veri tasarrufu, 2G/3G ve azaltılmış hareket tercihinde dekoratif videolar yüklenmez. Destekleyen masaüstü bağlantılarda tasarım aynı kalır.

TypeScript ve medya tercihi/SEO testleriyle kontrol edilir. Canlı hız kazanımı henüz ölçülmedi; yayın sonrasında aynı adresler tekrarlı ölçülmeli. Render uyku/soğuk başlangıç veya veritabanı bölge gecikmesi bu ölçümden kesinleştirilemez. Devam eden ilk açılış gecikmesinde servis planı, bölge ve veritabanı sorgu zamanları incelenmeli.

Kaynak: https://nextjs.org/docs/app/api-reference/functions/unstable_cache
