"""add credit sale collection history

Revision ID: k1f2a3b4c5d6
Revises: j0e1f2a3b4c5
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa


revision = "k1f2a3b4c5d6"
down_revision = "j0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "credit_sale_collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("finance_transfer_id", sa.Integer(), nullable=False),
        sa.Column("pos_reconciliation_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_credit_sale_collection_positive"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["finance_transfer_id"], ["finance_transfers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pos_reconciliation_id"], ["pos_reconciliations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finance_transfer_id"),
        sa.UniqueConstraint("pos_reconciliation_id"),
    )
    op.create_index("ix_credit_sale_collections_site_id", "credit_sale_collections", ["site_id"])
    op.create_index("ix_credit_sale_collections_store_id", "credit_sale_collections", ["store_id"])
    op.create_index("ix_credit_sale_collections_sale_id", "credit_sale_collections", ["sale_id"])
    op.create_index("ix_credit_sale_collections_payment_method", "credit_sale_collections", ["payment_method"])
    op.create_index("ix_credit_sale_collections_occurred_at", "credit_sale_collections", ["occurred_at"])


def downgrade():
    op.drop_index("ix_credit_sale_collections_occurred_at", table_name="credit_sale_collections")
    op.drop_index("ix_credit_sale_collections_payment_method", table_name="credit_sale_collections")
    op.drop_index("ix_credit_sale_collections_sale_id", table_name="credit_sale_collections")
    op.drop_index("ix_credit_sale_collections_store_id", table_name="credit_sale_collections")
    op.drop_index("ix_credit_sale_collections_site_id", table_name="credit_sale_collections")
    op.drop_table("credit_sale_collections")
