"""add site document numbers, count scans and session revision

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
"""

from alembic import op
import sqlalchemy as sa


revision = "a4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


DOCUMENT_TABLES = (
    ("sales", "sale"),
    ("returns", "return"),
    ("inventory_counts", "inventory_count"),
)


def _backfill_document_numbers(connection, table_name):
    counters = {}
    rows = connection.execute(
        sa.text(f"SELECT id, site_id FROM {table_name} ORDER BY site_id, id")
    ).mappings()
    for row in rows:
        site_id = int(row["site_id"])
        counters[site_id] = counters.get(site_id, 0) + 1
        connection.execute(
            sa.text(f"UPDATE {table_name} SET document_no = :document_no WHERE id = :id"),
            {"document_no": counters[site_id], "id": row["id"]},
        )
    return counters


def upgrade():
    connection = op.get_bind()

    op.add_column("sites", sa.Column("session_revision", sa.Integer(), nullable=False, server_default="1"))

    op.create_table(
        "site_document_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("site_id", "document_type", name="uq_site_document_sequences_site_type"),
    )
    op.create_index(
        "ix_site_document_sequences_site_id",
        "site_document_sequences",
        ["site_id"],
        unique=False,
    )

    for table_name, document_type in DOCUMENT_TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("document_no", sa.Integer(), nullable=True))

        counters = _backfill_document_numbers(connection, table_name)
        for site_id, last_value in counters.items():
            connection.execute(
                sa.text(
                    """
                    INSERT INTO site_document_sequences (site_id, document_type, last_value)
                    VALUES (:site_id, :document_type, :last_value)
                    """
                ),
                {
                    "site_id": site_id,
                    "document_type": document_type,
                    "last_value": last_value,
                },
            )

        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("document_no", existing_type=sa.Integer(), nullable=False)
            batch_op.create_index(f"ix_{table_name}_document_no", ["document_no"], unique=False)
            batch_op.create_unique_constraint(
                f"uq_{table_name}_site_document_no",
                ["site_id", "document_no"],
            )

    op.create_table(
        "inventory_count_scans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("inventory_count_id", sa.Integer(), nullable=False),
        sa.Column("inventory_count_line_id", sa.Integer(), nullable=False),
        sa.Column("product_barcode_id", sa.Integer(), nullable=False),
        sa.Column("barcode_value", sa.String(length=64), nullable=False),
        sa.Column("scanned_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["inventory_count_id"],
            ["inventory_counts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_count_line_id"],
            ["inventory_count_lines.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_barcode_id"],
            ["product_barcodes.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "inventory_count_id",
            "product_barcode_id",
            name="uq_inventory_count_scans_count_barcode",
        ),
    )
    for column_name in (
        "site_id",
        "store_id",
        "inventory_count_id",
        "inventory_count_line_id",
        "product_barcode_id",
    ):
        op.create_index(
            f"ix_inventory_count_scans_{column_name}",
            "inventory_count_scans",
            [column_name],
            unique=False,
        )

    connection.execute(
        sa.text(
            """
            UPDATE inventory_count_lines
            SET counted_quantity = 0
            WHERE inventory_count_id IN (
                SELECT id FROM inventory_counts WHERE status <> 'approved'
            )
            """
        )
    )


def downgrade():
    for column_name in (
        "product_barcode_id",
        "inventory_count_line_id",
        "inventory_count_id",
        "store_id",
        "site_id",
    ):
        op.drop_index(
            f"ix_inventory_count_scans_{column_name}",
            table_name="inventory_count_scans",
        )
    op.drop_table("inventory_count_scans")

    for table_name, _document_type in reversed(DOCUMENT_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(f"uq_{table_name}_site_document_no", type_="unique")
            batch_op.drop_index(f"ix_{table_name}_document_no")
            batch_op.drop_column("document_no")

    op.drop_index("ix_site_document_sequences_site_id", table_name="site_document_sequences")
    op.drop_table("site_document_sequences")
    op.drop_column("sites", "session_revision")
