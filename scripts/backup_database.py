"""Create a timestamped SQLite or PostgreSQL backup in BACKUP_DIR."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import hashlib
import json
import tempfile
from contextlib import closing
from uuid import uuid4
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import BASE_DIR, BaseConfig, normalize_database_url


def backup_database() -> Path:
    database_url = make_url(normalize_database_url(os.getenv("DATABASE_URL", BaseConfig.SQLALCHEMY_DATABASE_URI)))
    backup_dir = Path(os.getenv("BACKUP_DIR", str(BASE_DIR / "backups"))).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]

    if database_url.drivername.startswith("sqlite"):
        source_path = Path(database_url.database or "").resolve()
        if not source_path.is_file():
            raise RuntimeError(f"SQLite veritabanı bulunamadı: {source_path}")
        destination = backup_dir / f"ihrac-fazlasi-{timestamp}.sqlite3"
        with closing(sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True)) as source, closing(sqlite3.connect(destination)) as target:
            source.backup(target)
        verify_backup(destination)
        return destination

    if database_url.drivername.startswith("postgresql"):
        executable = shutil.which("pg_dump")
        if executable is None:
            raise RuntimeError("PostgreSQL yedeği için pg_dump kurulu olmalıdır.")
        destination = backup_dir / f"ihrac-fazlasi-{timestamp}.dump"
        environment = os.environ.copy()
        if database_url.password:
            environment["PGPASSWORD"] = database_url.password
        for parameter, variable in (("sslmode", "PGSSLMODE"), ("channel_binding", "PGCHANNELBINDING")):
            if parameter in database_url.query:
                environment[variable] = database_url.query[parameter]
        command = [
            executable,
            "--format=custom",
            "--no-owner",
            "--file",
            str(destination),
            "--host",
            database_url.host or "localhost",
            "--port",
            str(database_url.port or 5432),
            "--username",
            database_url.username or "postgres",
            database_url.database or "postgres",
        ]
        subprocess.run(command, check=True, env=environment, timeout=1800, capture_output=True)
        verify_backup(destination)
        return destination

    raise RuntimeError(f"Desteklenmeyen veritabanı türü: {database_url.drivername}")


def verify_backup(path: Path) -> dict:
    """Validate a backup, never restoring over the source database."""
    path = Path(path).resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Yedek dosyası boş veya bulunamadı.")
    restored = False
    if path.suffix == ".sqlite3":
        with tempfile.TemporaryDirectory(prefix="ihrac-restore-check-") as directory:
            restored_path = Path(directory) / "restored.sqlite3"
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as source, closing(sqlite3.connect(restored_path)) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise RuntimeError("Yedek bütünlük kontrolünden geçemedi.")
            restored = True
    elif path.suffix == ".dump":
        executable = shutil.which("pg_restore")
        if not executable:
            raise RuntimeError("PostgreSQL yedek kontrolü için pg_restore gereklidir.")
        subprocess.run([executable, "--list", str(path)], check=True, capture_output=True, timeout=120)
    else:
        raise RuntimeError("Desteklenmeyen yedek biçimi.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    manifest = dict(file=path.name, bytes=path.stat().st_size, sha256=digest.hexdigest(),
                    verified_at=datetime.now().isoformat(), restore_tested=restored,
                    verification="isolated_sqlite_restore" if restored else "postgres_archive_list_only")
    path.with_suffix(path.suffix + ".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    backup_path = backup_database()
    print(f"Yedek oluşturuldu: {backup_path}")
