"""add inventory count tables

Revision ID: f6a9c2d1e5b7
Revises: e4c8a1b2d3f4
Create Date: 2026-04-18 16:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a9c2d1e5b7"
down_revision = "e4c8a1b2d3f4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_counts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category_filter", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_counts_status"), "inventory_counts", ["status"], unique=False)

    op.create_table(
        "inventory_count_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("inventory_count_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("system_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("counted_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.ForeignKeyConstraint(["inventory_count_id"], ["inventory_counts.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_count_lines_inventory_count_id"), "inventory_count_lines", ["inventory_count_id"], unique=False)
    op.create_index(op.f("ix_inventory_count_lines_product_id"), "inventory_count_lines", ["product_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_inventory_count_lines_product_id"), table_name="inventory_count_lines")
    op.drop_index(op.f("ix_inventory_count_lines_inventory_count_id"), table_name="inventory_count_lines")
    op.drop_table("inventory_count_lines")

    op.drop_index(op.f("ix_inventory_counts_status"), table_name="inventory_counts")
    op.drop_table("inventory_counts")
