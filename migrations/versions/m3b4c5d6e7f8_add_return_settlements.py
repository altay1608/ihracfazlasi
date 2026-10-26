"""Preserve customer debt offsets separately from cash collections."""
from alembic import op
import sqlalchemy as sa
revision = 'm3b4c5d6e7f8'
down_revision = 'l2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table('return_settlements'):
        return
    op.create_table('return_settlements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('return_id', sa.Integer(), sa.ForeignKey('returns.id'), nullable=False, unique=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id'), nullable=False),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id'), nullable=False),
        sa.Column('credit_sale_id', sa.Integer(), sa.ForeignKey('sales.id'), index=True),
        sa.Column('current_entry_id', sa.Integer(), sa.ForeignKey('current_entries.id')),
        sa.Column('credit_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('cash_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('payment_method', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('credit_amount >= 0', name='ck_return_credit_nonnegative'))


def downgrade():
    raise RuntimeError('İade mahsup geçmişi otomatik silinemez.')
