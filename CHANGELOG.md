# Changelog

Bu dosya proje için sürüm/versiyon notlarını tutar.

Biçim olarak [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) yaklaşımı baz alınmıştır.
Proje henüz `1.0.0` öncesinde olduğu için sürüm yapısı operasyonel teslimata göre ilerletilecektir.

Bu dosya bundan sonraki tüm geliştirmelerde güncellenmelidir.

## [Unreleased]

### Added
- Admin ekranında sekmeleri daha görünür hale getiren kısa yol/kart yapısı eklendi.
- Ürün listesine `Perakende Çarpanı` kolonu eklendi.
- Ürün listesinde toplu seçim işlemleri için kompakt `Seçili İşlem` akışı eklendi.

### Verified
- `/products/` sayfasında ürün kodu ve perakende çarpanı görünürlüğü kontrol edildi.
- `/products/add` ve modal ürün formunda perakende çarpanı alanının render olduğu doğrulandı.
- `/admin/` ve `/admin/?tab=retail_multipliers` ekranlarında perakende çarpan yönetiminin görünür olduğu teyit edildi.
- Admin oluşturma/düzenleme formlarında `Vazgeç` akışının gerçek yönlendirme ile çalıştığı doğrulandı.

### Fixed
- Ürün ekleme modalında `parseLocaleNumber is not defined` kaynaklı açılış hatası giderildi.
- Ürün sayfasındaki gereksiz perakende çarpanı bilgilendirme paneli kaldırıldı.
- Ürün listesindeki üç ayrı toplu işlem butonu sadeleştirilerek tek kompakt akışa çekildi.
- Kârlılık raporundaki gereksiz indirim analitiği paneli kaldırıldı.
- Admin silme/toggle işlemlerinin yanlış yenileme URL'si kullanması düzeltildi.
- Tam sayfa iade/değişim formunun eski adet tabanlı şablonu kullanması düzeltildi.

### Changed
- Admin referans kayıtlarına aktif/pasif yönetimi eklendi.
- Ürün listesinde çoklu seçim mantığı, ayrı üst butonlar yerine işlemler sütunundaki ikonlarla birlikte çalışacak şekilde düzenlendi.
- İade/değişim ekranında barkod seçimi yanında barkod okutma ile seçme desteği eklendi.

## [0.9.0] - 2026-04-05

### Summary
- Proje boş Flask iskeletinden modüler, çok ekranlı bir butik ERP/POS uygulamasına taşındı.
- Ürün, stok, satış, iade/değişim, raporlama, dashboard ve temel veri yönetimi modülleri oluşturuldu.
- Arayüz çok sayıda iterasyonla butik temadan enterprise/dashboard çizgisine evrildi.
- Ürün veri modeli barkod odaklı yapıdan `ürün kodu + fiziksel barkod birimleri` yapısına geçirildi.

### Added
- Flask app factory, modüler blueprint mimarisi ve SQLAlchemy model ayrımı.
- Flask-Migrate entegrasyonu ve migration altyapısı.
- Dashboard/Lobby ekranı:
  - KPI kartları
  - satış grafiği
  - operasyon istasyonu
  - düşük stok ve çok satan ürün panelleri
- Ürün yönetimi:
  - ürün ekleme/düzenleme
  - stok güncelleme
  - barkodla ürün bulma
  - Excel şablon indirme/yükleme
  - çoklu seçimli toplu etiket
  - çoklu toplu düzenleme
  - çoklu toplu silme
- Satış/POS modülü:
  - barkod okutma ile sepete ürün ekleme
  - ödeme yöntemi seçimi
  - müşteri bilgileri için opsiyonel satış bilgi alanı
  - KDV ve yalın indirim hesap akışı
  - satış detayı ve termal fiş çıktısı
- İade/Değişim modülü:
  - satış ID üzerinden işlem başlatma
  - satış listesinden hızlı iade/değişim kısayolu
  - iade/değişim fişi
  - iade nedeni + serbest not alanı
- Raporlar:
  - tarih aralıklı günlük rapor
  - kârlılık raporu
  - indirim analitiği
- Admin paneli:
  - kategori yönetimi
  - varyant/beden yönetimi
  - ödeme yöntemi yönetimi
  - iade nedeni yönetimi
  - perakende çarpan tanımları
- Global modal sistemi:
  - ekle/düzenle modal akışları
  - silme onay modalı
  - AJAX submit ve kısmi liste yenileme
- Ortak tablo yetenekleri:
  - sütun gizle/göster
  - kolon sıralama
  - kolon yer değiştirme
  - Excel’e aktar
  - kolon bazlı filtreleme
  - sayfalama ve sayfa başına kayıt seçimi
- Busy overlay, toast bildirimi ve zorunlu alan işaretleyicileri.

### Changed
- Sol sidebar kaldırıldı, üst yatay navigasyona geçildi.
- Menü isimleri kurumsal/operasyonel isimlerle güncellendi.
- Dashboard/Lobby tasarımı birkaç kez elden geçirilerek daha kompakt ve standart hale getirildi.
- POS yerleşimi yeniden düzenlendi:
  - müşteri bilgileri ayrı panel
  - sepet ayrı panel
  - ödeme ayrı panel
- Ürün etiketi tasarımı referans görsellere göre birkaç kez yenilendi.
- Etiket baskı ölçüsü `40x20 mm` olarak revize edildi.
- Satış fişi 80mm termal yazıcıya uygun daha kompakt baskı yapısına çekildi.
- İade fişinde başlıklar Türkçeleştirildi ve sipariş tarihi eklendi.
- Günlük rapor tek tarihten iki tarih aralığına geçirildi.
- Ürün satış fiyatı manuel yapıdan `alış fiyatı x perakende çarpanı` modeline geçirildi.
- Barkod yapısı:
  - eski: ürün = barkod
  - yeni: `ürün kodu` ana kimlik, `ürün kodu-01/-02/...` fiziksel stok barkodları

### Fixed
- Modal içeriğinin hatalı JSON/ham metin görünmesi düzeltildi.
- Hover/kontrast problemleri ve dark/light çakışmaları temizlendi.
- Ürün listesi stok renkleri ve açıklama paleti netleştirildi.
- Satış detayından satış listesine geri dönme akışı düzeltildi.
- İade/değişim ekranında değişim alanının gereksiz yere açık kalması düzeltildi.
- İade fişi ve satış fişinde tarih/saat ve başlık sorunları düzeltildi.
- POS arama sonucu kutusunun gereksiz görünmesi düzeltildi.
- POS indirim alanındaki giriş davranışı düzeltildi.
- Logo tıklaması, geri butonu ve menü akışları kullanıcı dostu hale getirildi.
- Dashboard sağ panel yerleşim ve görünürlük sorunları düzeltildi.

### Database
- `Sale` modeline müşteri alanları eklendi.
- `Return` modeline not alanı eklendi.
- `RetailMultiplier` modeli eklendi.
- `Product` modeline `product_code` ve `retail_multiplier_id` eklendi.
- `ProductBarcode` modeli eklendi.
- `SaleItem` ile fiziksel barkod birimleri arasında ilişki kuruldu.
- Migration zinciri güncellendi ve uygulanabildiği doğrulandı.

### Printing and Barcode
- Tekil ürün etiketi ve toplu etiket baskısı eklendi.
- Satış fişi ve iade/değişim fişi baskısı eklendi.
- 13 haneli saf numerik barkodlar için EAN-13 desteği korundu.
- Yeni `ürün kodu-01` formatı için gerçek `Code39` SVG barkod üretimi eklendi.

### Operational Cleanup
- Test/demo verileri birden çok kez temizlendi.
- Son temizlikte aşağıdaki kayıtlar sıfırlandı:
  - kategoriler
  - varyantlar
  - ödeme yöntemleri
  - perakende çarpanları
  - iade nedenleri
  - ürünler
  - fiziksel barkod kayıtları
  - satışlar
  - satış kalemleri
  - iadeler
  - iade kalemleri

### Notes for Next Work
- Yeni veri girişinden önce `Yönetim` ekranında temel referans verileri yeniden oluşturulmalıdır.
- Yeni barkod yapısı artık fiziksel stok takibini destekler; POS ve iade ekranları bu yapıya göre çalışır.
- Bundan sonraki her geliştirme bu dosyada yeni bir sürüm ya da `Unreleased` altında kayıt altına alınmalıdır.

### Known Limitations / Not Done Yet
- Ortak tablo export tarafı hâlâ gerçek `.xlsx` yerine istemci taraflı `.xls` üretimi yapıyor.
- Barkod çıktıları Code39 olarak üretildi; eğer kullanılan el terminali/okuyucu yalnızca belirli barkod ailelerini destekliyorsa saha testine göre Code128’e geçiş değerlendirilebilir.
- Çoklu toplu düzenleme şu an kategori/varyant/perakende çarpanı alanlarıyla sınırlı.
- Sayfalama ortak JS katmanında çalışıyor; çok büyük veri setlerinde server-side pagination ihtiyacı ileride değerlendirilebilir.
