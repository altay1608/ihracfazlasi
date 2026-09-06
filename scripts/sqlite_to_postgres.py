"""Safely copy a frozen SQLite snapshot into a verified PostgreSQL target database."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Mapping
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import MetaData


SYSTEM_TABLES = {"alembic_version"}
BATCH_SIZE = 500
FINANCIAL_COLUMNS = {
    "products": ("purchase_price", "sale_price"),
    "sales": ("total_amount", "total_discount"),
    "sale_items": ("unit_price", "discount_amount"),
    "return_items": ("refund_amount",),
    "inventory_count_lines": ("unit_cost",),
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Frozen SQLite backup path")
    parser.add_argument("--target-url", required=True, help="PostgreSQL SQLAlchemy URL")
    parser.add_argument(
        "--expected-target-database",
        default="lafemme_preprod",
        help="Safety guard: import is rejected unless current_database() matches",
    )
    parser.add_argument(
        "--confirm-replace-target",
        action="store_true",
        help="Required before target table rows can be replaced",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate only; make no target changes")
    return parser.parse_args()


def quote_identifier(name: str) -> str:
    return f'"{name.replace(chr(34), chr(34) * 2)}"'


def table_count(connection: sa.Connection, table: sa.Table) -> int:
    return int(connection.scalar(sa.select(sa.func.count()).select_from(table)) or 0)


def table_total(connection: sa.Connection, table: sa.Table, column_name: str) -> Decimal:
    value = connection.scalar(
        sa.select(sa.func.coalesce(sa.func.sum(table.c[column_name]), 0)).select_from(table)
    )
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def chunks(rows: Iterable[Mapping[str, object]], size: int) -> Iterable[list[Mapping[str, object]]]:
    batch: list[Mapping[str, object]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def normalize_row(row: Mapping[str, object], target_table: sa.Table) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for column in target_table.columns:
        value = row[column.name]
        if isinstance(column.type, sa.Boolean) and value is not None:
            value = bool(value)
        normalized[column.name] = value
    return normalized


def read_revision(connection: sa.Connection, metadata: MetaData) -> str | None:
    version_table = metadata.tables.get("alembic_version")
    if version_table is None:
        return None
    return connection.scalar(sa.select(version_table.c.version_num))


def assert_schema_compatibility(
    source_metadata: MetaData, target_metadata: MetaData
) -> list[sa.Table]:
    source_names = {table.name for table in source_metadata.tables.values()}
    target_names = {table.name for table in target_metadata.tables.values()}
    if source_names != target_names:
        raise RuntimeError(
            "Kaynak ve hedef tablo setleri esit degil. "
            f"Sadece kaynakta: {sorted(source_names - target_names)}; "
            f"sadece hedefte: {sorted(target_names - source_names)}"
        )

    target_tables = [table for table in target_metadata.sorted_tables if table.name not in SYSTEM_TABLES]
    for target_table in target_tables:
        source_table = source_metadata.tables[target_table.name]
        source_columns = [column.name for column in source_table.columns]
        target_columns = [column.name for column in target_table.columns]
        if source_columns != target_columns:
            raise RuntimeError(
                f"{target_table.name} sutunlari esit degil. "
                f"Kaynak: {source_columns}; hedef: {target_columns}"
            )
    return target_tables


def reset_sequences(connection: sa.Connection, tables: list[sa.Table]) -> None:
    for table in tables:
        if "id" not in table.c:
            continue
        qualified_name = f"{table.schema or 'public'}.{table.name}"
        sequence_name = connection.scalar(
            sa.text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
            {"table_name": qualified_name},
        )
        if not sequence_name:
            continue
        row_count = table_count(connection, table)
        if row_count:
            last_value = connection.scalar(sa.select(sa.func.max(table.c.id)).select_from(table))
            is_called = True
        else:
            last_value = 1
            is_called = False
        connection.execute(
            sa.text("SELECT setval(CAST(:sequence_name AS regclass), :last_value, :is_called)"),
            {
                "sequence_name": sequence_name,
                "last_value": int(last_value),
                "is_called": is_called,
            },
        )


def validate_copy(
    source_connection: sa.Connection,
    target_connection: sa.Connection,
    source_metadata: MetaData,
    target_metadata: MetaData,
    tables: list[sa.Table],
) -> None:
    mismatches: list[str] = []
    for target_table in tables:
        source_table = source_metadata.tables[target_table.name]
        source_count = table_count(source_connection, source_table)
        target_count = table_count(target_connection, target_table)
        if source_count != target_count:
            mismatches.append(
                f"{target_table.name}: kaynak={source_count}, hedef={target_count}"
            )

    for table_name, column_names in FINANCIAL_COLUMNS.items():
        if table_name not in source_metadata.tables:
            continue
        for column_name in column_names:
            source_total = table_total(
                source_connection, source_metadata.tables[table_name], column_name
            )
            target_total = table_total(
                target_connection, target_metadata.tables[table_name], column_name
            )
            if source_total != target_total:
                mismatches.append(
                    f"{table_name}.{column_name}: kaynak={source_total}, hedef={target_total}"
                )

    if mismatches:
        raise RuntimeError("Aktarim dogrulamasi basarisiz:\n- " + "\n- ".join(mismatches))


def print_source_summary(source_connection: sa.Connection, source_metadata: MetaData, tables: list[sa.Table]) -> None:
    print("KAYNAK_OZETI")
    for table in tables:
        print(f"{table.name}={table_count(source_connection, source_metadata.tables[table.name])}")


def main() -> int:
    args = parse_arguments()
    source_path = Path(args.source).expanduser().resolve()
    if not source_path.is_file() or source_path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise RuntimeError(f"Gecerli bir SQLite snapshot bulunamadi: {source_path}")
    if args.dry_run and args.confirm_replace_target:
        raise RuntimeError("Dry-run ve hedefi degistirme onayi birlikte kullanilamaz.")
    if not args.dry_run and not args.confirm_replace_target:
        raise RuntimeError("Hedef veriyi degistirmek icin --confirm-replace-target zorunludur.")

    source_url = f"sqlite+pysqlite:///{source_path.as_posix()}"
    source_engine = sa.create_engine(source_url, future=True)
    target_engine = sa.create_engine(args.target_url, future=True, pool_pre_ping=True)

    try:
        with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
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

            print(f"HEDEF_DOGRULAMA database={target_database} revision={target_revision}")
            print_source_summary(source_connection, source_metadata, tables)
            if args.dry_run:
                print("DRY_RUN_BASARILI: hedefte hicbir veri degistirilmedi.")
                return 0

            quoted_tables = ", ".join(quote_identifier(table.name) for table in tables)
            target_connection.execute(sa.text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))

            for target_table in tables:
                source_table = source_metadata.tables[target_table.name]
                source_rows = source_connection.execute(sa.select(source_table)).mappings()
                inserted_rows = 0
                for batch in chunks(source_rows, BATCH_SIZE):
                    values = [normalize_row(row, target_table) for row in batch]
                    target_connection.execute(target_table.insert(), values)
                    inserted_rows += len(values)
                print(f"AKTARILDI {target_table.name}={inserted_rows}")

            reset_sequences(target_connection, tables)
            validate_copy(
                source_connection,
                target_connection,
                source_metadata,
                target_metadata,
                tables,
            )
            print("AKTARIM_DOGRULANDI: tablo sayimlari ve mali toplamlar eslesti.")
        print(f"AKTARIM_BASARILI: PostgreSQL {target_database} verisi commit edildi.")
        return 0
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"AKTARIM_BASARISIZ: {error}", file=sys.stderr)
        raise SystemExit(1)
