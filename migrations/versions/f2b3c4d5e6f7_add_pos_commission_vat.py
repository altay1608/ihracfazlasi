"""track VAT on POS commission

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "f2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pos_reconciliations") as batch_op:
        batch_op.add_column(sa.Column("commission_vat_rate", sa.Numeric(5, 2), server_default="10.00", nullable=False))
        batch_op.add_column(sa.Column("commission_vat_amount", sa.Numeric(14, 2), server_default="0", nullable=False))
        batch_op.create_check_constraint(
            "ck_pos_reconciliation_commission_vat_nonnegative",
            "commission_vat_amount >= 0",
        )


def downgrade():
    with op.batch_alter_table("pos_reconciliations") as batch_op:
        batch_op.drop_constraint("ck_pos_reconciliation_commission_vat_nonnegative", type_="check")
        batch_op.drop_column("commission_vat_amount")
        batch_op.drop_column("commission_vat_rate")
