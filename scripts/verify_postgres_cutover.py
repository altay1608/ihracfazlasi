"""Read-only validation for a SQLite-to-PostgreSQL production cutover."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import MetaData

from sqlite_to_postgres import (
    assert_schema_compatibility,
    read_revision,
    table_count,
    validate_copy,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Frozen SQLite snapshot path")
    parser.add_argument("--target-url", required=True, help="PostgreSQL SQLAlchemy URL")
    parser.add_argument(
        "--expected-target-database",
        default="lafemme_prod",
        help="Safety guard: verification stops unless current_database() matches",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    source_path = Path(args.source).expanduser().resolve()
    if not source_path.is_file() or source_path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise RuntimeError(f"Gecerli bir SQLite snapshot bulunamadi: {source_path}")

    source_engine = sa.create_engine(f"sqlite+pysqlite:///{source_path.as_posix()}", future=True)
    target_engine = sa.create_engine(args.target_url, future=True, pool_pre_ping=True)
    try:
        with source_engine.connect() as source_connection, target_engine.connect() as target_connection:
            target_database = target_connection.scalar(sa.text("SELECT current_database()"))
            if target_database != args.expected_target_database:
                raise RuntimeError(
                    f"Guvenlik durdurmasi: hedef '{target_database}', "
                    f"beklenen '{args.expected_target_database}'."
                )

            source_metadata = MetaData()
            target_metadata = MetaData()
            source_metadata.reflect(bind=source_connection)
            target_metadata.reflect(bind=target_connection)
            tables = assert_schema_compatibility(source_metadata, target_metadata)

            source_revision = read_revision(source_connection, source_metadata)
            target_revision = read_revision(target_connection, target_metadata)
            if source_revision != target_revision:
                raise RuntimeError(
                    f"Alembic revision uyusmuyor: kaynak={source_revision}, hedef={target_revision}."
                )

            validate_copy(
                source_connection,
                target_connection,
                source_metadata,
                target_metadata,
                tables,
            )
            table_summary = ", ".join(
                f"{table.name}={table_count(target_connection, table)}" for table in tables
            )
            print(
                "POSTGRES_CUTOVER_DOGRULANDI "
                f"database={target_database} revision={target_revision} {table_summary}"
            )
        return 0
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"POSTGRES_CUTOVER_DOGRULAMA_BASARISIZ: {error}", file=sys.stderr)
        raise SystemExit(1)
