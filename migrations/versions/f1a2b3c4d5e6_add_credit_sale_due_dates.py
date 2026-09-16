"""add credit sale due dates

Revision ID: f1a2b3c4d5e6
Revises: e83c1b2d4f90
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e83c1b2d4f90"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sales") as batch_op:
        batch_op.add_column(sa.Column("payment_due_date", sa.Date(), nullable=True))
        batch_op.create_index("ix_sales_payment_due_date", ["payment_due_date"], unique=False)


def downgrade():
    with op.batch_alter_table("sales") as batch_op:
        batch_op.drop_index("ix_sales_payment_due_date")
        batch_op.drop_column("payment_due_date")
