# Finans ekranı: kısa kullanım rehberi

## Hangi işlem nereden yapılır?

| Yapmak istediğiniz işlem | Ekran | Sonuç |
|---|---|---|
| Kargo, kira, elektrik gibi masraf ödemek | Masraf Gir | Onaylanan tutar seçilen hesaptan düşer. |
| Toptancıdan borçla mal almak | Borçlar ve Alacaklar → Yeni kişi / firma veya borç / alacak ekle | Borç oluşur; henüz para çıkmaz. |
| Toptancı borcunun bir kısmını ödemek | Açık borç satırı → Ödeme yap | Borç azalır, seçilen hesap azalır. Ayrıca masraf girilmez. |
| Veresiye satışın ödemesini almak | Veresiye Tahsilatı → İlgili fiş → Ödeme Al | Satış borcu azalır, seçilen tahsilat hesabı artar. Ayrıca cari tahsilat girilmez. |
| Kasadaki nakdi bankaya yatırmak | Para Aktar | Kasa azalır, banka artar; yeni gider veya ciro oluşmaz. |
| Ortak para çekimi gibi diğer hareketler | Diğer İşlemler → Diğer Para Giriş / Çıkışı | Seçilen hesabı etkiler. İşletme gideri işaretini işlemin niteliğine göre seçin. |
| Maaş veya düzenli borç ödemek | Diğer İşlemler → Maaş ve Dönemsel Borçlar | İlgili borç üzerinden ödeme yapılır; masraf ekranından tekrar girilmez. |
| Yanlış kaydı düzeltmek | Belgeler ve Kontroller → İşlem Düzeltme | Desteklenen işlemler ters kayıtla düzeltilir; geçmiş silinmez. |

## Rakamlar ne anlama geliyor?

- **Kasa + banka:** Sisteme göre kullanılabilir para; bankadan otomatik doğrulanmış bakiye değildir.
- **POS'tan gelecek:** Henüz banka hesabına aktarılmamış kart bakiyesi.
- **Bekleyen veresiye:** Tüm tarihlerdeki tahsil edilmemiş alacak hesabı; kasa parası değildir. Müşteri/fiş listesiyle kapsam farklılığı varsa kayıtlar eşleştirilmelidir.
- **Toptancı borcu:** Ödenmemiş borç; hazır paradan otomatik düşülmüş değildir.
- **Toplam satış · veresiye dahil:** Seçilen ayın finans kayıt tarihine göre satış ve değişimler, iadeler ve ters kayıtlar sonrası KDV dahil tutar. Kasaya giren para değildir.
- **Net tahsil edilen:** Seçilen dönemde satışlardan ve veresiye ödemelerinden alınan tutar, iadeler ve ters kayıtlar sonrası. Nakit, havale/EFT ve kart ayrı gösterilir. Kart tutarı komisyon öncesidir; henüz bankaya geçmemiş olabilir. Önceki ayın veresiye ödemesi, ödendiği ayın tahsilatına girer; yeniden ciro oluşturmaz. Kasa/banka ve POS/banka aktarımları tekrar tahsilat sayılmaz. Açılış bakiyesi, manuel gelir ve ayrı cari tahsilatlar bu satış tahsilatı özetine dahil değildir. İade veya iptal fazla ise dönem neti eksi olabilir.
- **Ödeme ve diğer çıkışlar:** Cari borç ödemeleri, manuel çıkışlar, dönemsel borç ödemeleri ve POS komisyonları. Ortak çekimleri de bulunabilir; tamamı işletme gideri değildir.
- **Kâr:** Satılan ürünlerin maliyeti ve ilgili giderlere göre hesaplanır. Ciro eksi yapılan ödemeler kâr değildir.
- **Gider planı:** Tahmindir; tek başına kasadan ödeme oluşturmaz.

Ay seçimi yalnız aylık özeti değiştirir; hesap bakiyeleri günceldir. Para Hareketleri ekranı en yeni 500 kaydı gösterir; eski kayıtlar için tarih aralığını daraltın.

## Kayıtların korunması

Bu düzenleme mevcut hareketleri silmez, bakiyeleri yeniden yazmaz ve veritabanı şemasını değiştirmez. Eski kapalı borçlar ve ödeme geçmişi açılır bölümlerde korunur. Olası çift kayıtlar gerçek belge/ödemelerle doğrulanmadan otomatik düzeltilmez.
