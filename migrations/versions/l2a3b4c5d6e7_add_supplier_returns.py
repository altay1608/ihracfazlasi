"""Add supplier return history without changing existing records."""
from alembic import op
import sqlalchemy as sa

revision = "l2a3b4c5d6e7"
down_revision = "k1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table("supplier_returns"):
        return
    op.create_table("supplier_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("current_accounts.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("product_name", sa.String(150), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("current_entry_id", sa.Integer(), sa.ForeignKey("current_entries.id")),
        sa.Column("movement_id", sa.Integer(), sa.ForeignKey("finance_movements.id")),
        sa.Column("barcode_values", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("request_key", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("site_id", "store_id", "request_key", name="uq_supplier_return_request"),
        sa.CheckConstraint("quantity > 0 AND amount > 0", name="ck_supplier_return_positive"))


def downgrade():
    raise RuntimeError("İade geçmişi korunmalıdır; otomatik tablo silme kapalıdır.")
