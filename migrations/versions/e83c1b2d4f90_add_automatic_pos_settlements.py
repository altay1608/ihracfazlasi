"""add automatic POS settlement tracking

Revision ID: e83c1b2d4f90
Revises: d72f8a1c4e90
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "e83c1b2d4f90"
down_revision = "d72f8a1c4e90"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("finance_activations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "pos_commission_rate",
                sa.Numeric(precision=7, scale=4),
                server_default="2.5500",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("pos_settlement_days", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.add_column(sa.Column("pos_bank_account_id", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_finance_activation_pos_rate",
            "pos_commission_rate >= 0 AND pos_commission_rate < 100",
        )
        batch_op.create_check_constraint(
            "ck_finance_activation_pos_days",
            "pos_settlement_days >= 0 AND pos_settlement_days <= 365",
        )
        batch_op.create_foreign_key(
            "fk_finance_activations_pos_bank_account_id_finance_accounts",
            "finance_accounts",
            ["pos_bank_account_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    with op.batch_alter_table("pos_reconciliations") as batch_op:
        batch_op.add_column(sa.Column("sale_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("expected_settlement_date", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("status", sa.String(length=20), server_default="settled", nullable=False)
        )
        batch_op.add_column(sa.Column("settled_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("auto_generated", sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.create_foreign_key(
            "fk_pos_reconciliations_sale_id_sales",
            "sales",
            ["sale_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint("uq_pos_reconciliation_sale", ["sale_id"])
        batch_op.create_check_constraint(
            "ck_pos_reconciliation_status",
            "status IN ('pending','settled','cancelled')",
        )
        batch_op.create_index(
            "ix_pos_reconciliations_expected_settlement_date",
            ["expected_settlement_date"],
            unique=False,
        )
        batch_op.create_index(
            "ix_pos_reconciliations_status", ["status"], unique=False
        )
        batch_op.create_index(
            "ix_pos_reconciliations_auto_generated", ["auto_generated"], unique=False
        )

    op.execute(
        "UPDATE pos_reconciliations SET settled_at = occurred_at "
        "WHERE settled_at IS NULL AND status = 'settled'"
    )


def downgrade():
    with op.batch_alter_table("pos_reconciliations") as batch_op:
        batch_op.drop_index("ix_pos_reconciliations_auto_generated")
        batch_op.drop_index("ix_pos_reconciliations_status")
        batch_op.drop_index("ix_pos_reconciliations_expected_settlement_date")
        batch_op.drop_constraint("ck_pos_reconciliation_status", type_="check")
        batch_op.drop_constraint("uq_pos_reconciliation_sale", type_="unique")
        batch_op.drop_constraint(
            "fk_pos_reconciliations_sale_id_sales", type_="foreignkey"
        )
        batch_op.drop_column("auto_generated")
        batch_op.drop_column("settled_at")
        batch_op.drop_column("status")
        batch_op.drop_column("expected_settlement_date")
        batch_op.drop_column("sale_id")

    with op.batch_alter_table("finance_activations") as batch_op:
        batch_op.drop_constraint(
            "fk_finance_activations_pos_bank_account_id_finance_accounts",
            type_="foreignkey",
        )
        batch_op.drop_constraint("ck_finance_activation_pos_days", type_="check")
        batch_op.drop_constraint("ck_finance_activation_pos_rate", type_="check")
        batch_op.drop_column("pos_bank_account_id")
        batch_op.drop_column("pos_settlement_days")
        batch_op.drop_column("pos_commission_rate")
