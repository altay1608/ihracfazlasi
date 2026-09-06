"""add critical stock level fields

Revision ID: e4c8a1b2d3f4
Revises: 9b4d2f11a6c3
Create Date: 2026-04-18 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e4c8a1b2d3f4"
down_revision = "9b4d2f11a6c3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("critical_stock_level", sa.Integer(), nullable=True))

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("critical_stock_level", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_column("critical_stock_level")

    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_column("critical_stock_level")
