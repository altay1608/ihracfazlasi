"""initial schema

Revision ID: ae7fa00fe70c
Revises:
Create Date: 2026-03-20 09:11:41.596694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae7fa00fe70c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_categories_name'), ['name'], unique=True)

    op.create_table('payment_methods',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('payment_methods', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_payment_methods_name'), ['name'], unique=True)

    op.create_table('return_reasons',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('return_reasons', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_return_reasons_name'), ['name'], unique=True)

    op.create_table('variants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('variants', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_variants_name'), ['name'], unique=True)

    op.create_table('products',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=False),
    sa.Column('barcode', sa.String(length=64), nullable=False),
    sa.Column('purchase_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('sale_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('stock_quantity', sa.Integer(), nullable=False),
    sa.Column('variant', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('barcode', name='uq_products_barcode')
    )
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_products_barcode'), ['barcode'], unique=True)

    op.create_table('sales',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sale_date', sa.DateTime(), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('total_discount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('payment_method', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sales', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_sales_sale_date'), ['sale_date'], unique=False)

    op.create_table('sale_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sale_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('returns',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('original_sale_id', sa.Integer(), nullable=False),
    sa.Column('return_date', sa.DateTime(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['original_sale_id'], ['sales.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('returns', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_returns_original_sale_id'), ['original_sale_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_returns_return_date'), ['return_date'], unique=False)

    op.create_table('return_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('return_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('refund_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['return_id'], ['returns.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('return_items')
    with op.batch_alter_table('returns', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_returns_return_date'))
        batch_op.drop_index(batch_op.f('ix_returns_original_sale_id'))

    op.drop_table('returns')
    op.drop_table('sale_items')
    with op.batch_alter_table('sales', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sales_sale_date'))

    op.drop_table('sales')
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_products_barcode'))

    op.drop_table('products')
    with op.batch_alter_table('variants', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_variants_name'))

    op.drop_table('variants')
    with op.batch_alter_table('return_reasons', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_return_reasons_name'))

    op.drop_table('return_reasons')
    with op.batch_alter_table('payment_methods', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payment_methods_name'))

    op.drop_table('payment_methods')
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_categories_name'))

    op.drop_table('categories')
