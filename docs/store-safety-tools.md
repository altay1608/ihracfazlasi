# Mağaza güvenlik ve takip araçları

## Kullanım
- Lobby → Gün Sonu Kasa: sayılan nakit ile seçili günün sonundaki bakiye karşılaştırılır. Kart ve banka net hareketleri ayrı gösterilir. Kasa farkı açıklamaya yazılır; otomatik kasa düzeltmesi yapılmaz.
- Finans → İşlem Düzeltme: masraf, transfer veya veresiye tahsilatı için neden girilir. Asıl kayıt silinmez; bugüne ters kayıt eklenir. Bankaya geçmiş kart tahsilatı otomatik iptal edilmez.
- Lobby → Ödeme Ajandası: geciken, bugün ve 7 gün içinde vadeli alacak/borçlar ile beklenen POS tutarları. Ödeme kendiliğinden yapılmaz.
- Lobby → Satılmayan Ürünler: stokta olup 30/60/90/180 gündür satılmamış ürünler; stoklar değişmez.
- Lobby → Müşteri Geçmişi: kayıtlı telefonun birebir eşleşmesiyle satış, ürün, beden, fiş, iade ve veresiye bakiyesi. Aynı isimli kişiler birleştirilmez.

## Otomatik yedek: başlangıçta KAPALI
Canlı veri bu geliştirme sırasında kopyalanmaz veya herhangi bir buluta gönderilmez.
GitHub deposunda yalnızca sahibi tarafından seçilmiş özel AWS S3 kovası kullanılmalıdır.
Gerekli secrets: BACKUP_DATABASE_URL (doğrudan PostgreSQL bağlantısı), BACKUP_S3_BUCKET,
BACKUP_AWS_ACCESS_KEY_ID, BACKUP_AWS_SECRET_ACCESS_KEY. Kimliğin yalnız bu kova/önek üzerinde PutObject ve GetObject izni olmalıdır.
Variables: BACKUP_AWS_REGION ve ENABLE_DATABASE_BACKUP=true. Bu son ayar verilmedikçe zamanlanmış iş çalışmaz.
Günlük saat: 00:00 UTC / Türkiye 03:00. GitHub zamanlamaları gecikebilir.
PostgreSQL istemcisi 17 kullanılır; sunucu daha yeni ise etkinleştirmeden önce eşleşen sürüm seçilmelidir.
Kovada public erişim engellenmeli, versioning ve uygun saklama politikası kullanıcı tarafından kurulmalıdır.
Dosyalar GitHub artifact olarak yüklenmez. Yedekler S3 sunucu tarafında şifrelenir.
Bu iş veritabanını kapsar; harici yüklenmiş dosyalar, servis ayarları ve sırlar ayrıca yedeklenmelidir.

SQLite yedeği geçici ayrı dosyaya geri yüklenerek integrity_check ile doğrulanır.
PostgreSQL yedeğinde pg_restore --list yalnız arşiv yapısını doğrular; başarılı gerçek geri yükleme anlamına gelmez.
Canlıya dokunmadan gerçek PostgreSQL geri yükleme testi için ayrı, boş bir test veritabanı ve sahip onayı gerekir.
Etkinleştirme kabulü: manuel başarılı çalıştırma, özel depoda dosya/doğrulama raporu, ayrı test ortamında geri yükleme ve başarısız iş bildirimleri kontrol edilmelidir.

## Test planı
- Finans: geçmiş gün kesimi, ters kaydın tek kez işlemesi, transferin iki ayağı, veresiye bakiyesinin geri açılması, kapalı dönem ve yanlış mağaza reddi.
- Salt-okunur ekranlar: mağaza izolasyonu, vadesiz ve gecikmiş kayıt, sıfır stokun hariç tutulması, müşteri isimlerinin karışmaması.
- Yedek: kaynak değişmeden izole geri yükleme, bütünlük ve SHA-256 raporu, eksik hedefte dışarı veri gönderilmemesi.
- Regresyon: tüm mevcut testler; canlı stokta deneme satışı yapılmaz.
