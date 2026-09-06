"""Create a timestamped SQLite or PostgreSQL backup in BACKUP_DIR."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
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
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if database_url.drivername.startswith("sqlite"):
        source_path = Path(database_url.database or "").resolve()
        if not source_path.is_file():
            raise RuntimeError(f"SQLite veritabanı bulunamadı: {source_path}")
        destination = backup_dir / f"ihrac-fazlasi-{timestamp}.sqlite3"
        with sqlite3.connect(source_path) as source, sqlite3.connect(destination) as target:
            source.backup(target)
        return destination

    if database_url.drivername.startswith("postgresql"):
        executable = shutil.which("pg_dump")
        if executable is None:
            raise RuntimeError("PostgreSQL yedeği için pg_dump kurulu olmalıdır.")
        destination = backup_dir / f"ihrac-fazlasi-{timestamp}.dump"
        environment = os.environ.copy()
        if database_url.password:
            environment["PGPASSWORD"] = database_url.password
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
        subprocess.run(command, check=True, env=environment)
        return destination

    raise RuntimeError(f"Desteklenmeyen veritabanı türü: {database_url.drivername}")


if __name__ == "__main__":
    backup_path = backup_database()
    print(f"Yedek oluşturuldu: {backup_path}")
