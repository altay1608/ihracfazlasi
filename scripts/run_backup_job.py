"""Scheduled, private S3 backup. Requires explicit destination configuration."""
import json
import os
from pathlib import Path
from backup_database import backup_database


def main():
    if not os.environ.get("DATABASE_URL", "").strip():
        raise RuntimeError("Yedeklenecek veritabanı açıkça tanımlanmalıdır.")
    bucket = os.environ.get("BACKUP_S3_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("Özel yedek kovası tanımlanmadı; yedekleme başlatılmadı.")
    import boto3
    path = backup_database()
    manifest_path = path.with_suffix(path.suffix + ".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    client = boto3.client("s3")
    prefix = os.environ.get("BACKUP_S3_PREFIX", "ihracfazlasi").strip("/")
    key = f"{prefix}/{path.name}"
    client.upload_file(str(path), bucket, key, ExtraArgs={
        "ServerSideEncryption": "AES256", "Metadata": {"sha256": manifest["sha256"]},
    })
    uploaded = client.head_object(Bucket=bucket, Key=key)
    if uploaded["ContentLength"] != manifest["bytes"] or uploaded.get("Metadata", {}).get("sha256") != manifest["sha256"]:
        raise RuntimeError("Uzak yedek doğrulanamadı.")
    client.upload_file(str(manifest_path), bucket, key + ".json", ExtraArgs={"ServerSideEncryption": "AES256"})
    print("Şifreli özel depolamaya yedek ve doğrulama raporu kaydedildi.")
    if not manifest["restore_tested"]:
        print("PostgreSQL arşivi doğrulandı; ayrı veritabanına gerçek geri yükleme testi ayrıca gereklidir.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Connection URLs, provider responses and passwords must not enter CI logs.
        print("Yedekleme başarısız. Yapılandırmayı ve sağlayıcı erişimini kontrol edin.")
        raise SystemExit(1)
