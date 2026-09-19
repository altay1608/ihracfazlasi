"""add split sale payment allocations"""

from alembic import op
import sqlalchemy as sa


revision = "i9d0e1f2a3b4"
down_revision = "h8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sale_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PAID"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_sale_payment_amount_positive"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_payments_sale_id", "sale_payments", ["sale_id"], unique=False)
    op.create_index("ix_sale_payments_payment_method", "sale_payments", ["payment_method"], unique=False)
    op.create_index("ix_sale_payments_due_date", "sale_payments", ["due_date"], unique=False)
    op.create_index("ix_sale_payments_status", "sale_payments", ["status"], unique=False)


def downgrade():
    op.drop_index("ix_sale_payments_status", table_name="sale_payments")
    op.drop_index("ix_sale_payments_due_date", table_name="sale_payments")
    op.drop_index("ix_sale_payments_payment_method", table_name="sale_payments")
    op.drop_index("ix_sale_payments_sale_id", table_name="sale_payments")
    op.drop_table("sale_payments")
