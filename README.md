# İhraç Fazlası Giyim

Flask + SQLite tabanli butik ERP/POS uygulamasi.

## Proje Yapisi

- Depo koku: magazanin yonetim ve on muhasebe paneli (Flask)
- `site/`: ihracfazlasigiyim.com web sitesi ve web admin alani (Next.js)

Web sitesini Vercel'e baglarken **Root Directory** degeri `site` olmalidir.
Yonetim paneli ayri bir Vercel projesi olarak yayinlanacaksa Root Directory bos
birakilir.

## Kurulum

```powershell
pip install -r requirements.txt
```

## Veritabani

```powershell
python -m flask --app run.py db upgrade
```

Yeni migration olusturmak icin:

```powershell
python -m flask --app run.py db migrate -m "aciklama"
python -m flask --app run.py db upgrade
```

## Uygulamayi Calistirma

```powershell
python run.py
```

## Giris Koruma

Uygulama varsayilan olarak login ister. Canli ortamda asagidaki ortam degiskenlerini mutlaka ayarla:

```powershell
$env:SECRET_KEY="uzun-rastgele-bir-secret"
$env:AUTH_USERNAME="admin"
$env:AUTH_PASSWORD="guclu-bir-sifre"
```

Panelde sag ustteki `admin` menusunden `Kullanici Bilgileri` sayfasina girerek sifre degistirilebilir.
Degistirilen sifre `AUTH_SETTINGS_PATH` ile belirtilen dosyada hash olarak saklanir.

Canli ortamda varsayilan `SECRET_KEY` veya varsayilan sifre ile production modunda baslatmaya izin verilmez.
Login formlarinda CSRF token, hatali denemelerde gecici kilitleme, guvenli session cookie ayarlari ve temel guvenlik headerlari aktiftir.

Gerekirse gecici olarak login korumasini kapatmak icin:

```powershell
$env:AUTH_ENABLED="0"
```

## Demo Veri

```powershell
python seed_data.py
```

Seed scripti 30 urun, 80 satis ve iade/degisim kayitlari ile gercekci bir demo senaryosu kurar.

## Veritabani Yedegi

Calisan veritabaninin tarih damgali yedegini almak icin:

```powershell
python scripts/backup_database.py
```

Yedekler varsayilan olarak `backups` klasorune yazilir. Canli ortamda `BACKUP_DIR`
kalici ve tercihen sunucu disinda eslenen bir konuma ayarlanmalidir. PostgreSQL icin
sunucuda `pg_dump` aracinin kurulu olmasi gerekir.

## Notlar

- Varsayilan veritabani dosyasi `lafemme.db`'dir.
- Gerekirse farkli bir SQLite dosyasi ile calismak icin `DATABASE_URL` ortam degiskeni kullanilabilir.
- Ilk migration dosyasi taze kurulumda tam semayi olusturacak sekilde guncellenmistir.

