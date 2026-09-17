"""add sale item line types for gifts and personal use"""

from alembic import op
import sqlalchemy as sa


revision = "h8c9d0e1f2a3"
down_revision = "g7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.add_column(
            sa.Column("line_type", sa.String(length=20), nullable=False, server_default="sale")
        )
        batch_op.create_index("ix_sale_items_line_type", ["line_type"], unique=False)


def downgrade():
    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.drop_index("ix_sale_items_line_type")
        batch_op.drop_column("line_type")
