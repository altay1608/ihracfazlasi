"""add audit logs and inventory transaction history

Revision ID: c3d4e5f6a7b8
Revises: f6a9c2d1e5b7
Create Date: 2026-08-18 22:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "f6a9c2d1e5b7"
branch_labels = None
depends_on = None


def upgrade():
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "postgresql":
        timestamp_expression = "CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul'"
    elif dialect_name == "sqlite":
        timestamp_expression = "datetime('now', '+3 hours')"
    else:
        timestamp_expression = "CURRENT_TIMESTAMP"

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("key"),
    )
    op.bulk_insert(
        sa.table("system_settings", sa.column("key", sa.String()), sa.column("value", sa.String())),
        [{"key": "audit_logging_enabled", "value": "1"}],
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("actor_username", sa.String(length=120), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("endpoint", sa.String(length=160), nullable=True),
        sa.Column("request_method", sa.String(length=12), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_occurred_at"), "audit_logs", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_username"), "audit_logs", ["actor_username"], unique=False)
    op.create_index(op.f("ix_audit_logs_event_type"), "audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_code", sa.String(length=40), nullable=False),
        sa.Column("transaction_name", sa.String(length=140), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("product_code", sa.String(length=32), nullable=False),
        sa.Column("barcode_values", sa.String(length=500), nullable=True),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("quantity_before", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("source_reference", sa.String(length=160), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_username", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_transactions_transaction_code"), "inventory_transactions", ["transaction_code"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_occurred_at"), "inventory_transactions", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_product_id"), "inventory_transactions", ["product_id"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_product_code"), "inventory_transactions", ["product_code"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_source_type"), "inventory_transactions", ["source_type"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_source_id"), "inventory_transactions", ["source_id"], unique=False)

    op.execute(
        f"""
        INSERT INTO inventory_transactions (
            transaction_code, transaction_name, occurred_at, product_id, product_name, product_code,
            quantity_delta, quantity_before, quantity_after, unit_cost, total_cost,
            source_type, source_reference, note, created_at
        )
        SELECT
            'OPENING-BAL', 'Başlangıç Stok Devri', {timestamp_expression}, id, name, product_code,
            stock_quantity, 0, stock_quantity, purchase_price, stock_quantity * purchase_price,
            'system', 'GO-LIVE', 'İşlem tarihçesi devreye alma stoğu', {timestamp_expression}
        FROM products
        WHERE stock_quantity <> 0
        """
    )


def downgrade():
    op.drop_index(op.f("ix_inventory_transactions_source_id"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_source_type"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_product_code"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_product_id"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_occurred_at"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_transaction_code"), table_name="inventory_transactions")
    op.drop_table("inventory_transactions")

    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_event_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_username"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_occurred_at"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("system_settings")
