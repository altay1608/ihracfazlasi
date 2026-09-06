"""add sale customer fields

Revision ID: b9c4d7f13b2d
Revises: ae7fa00fe70c
Create Date: 2026-03-23 11:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b9c4d7f13b2d"
down_revision = "ae7fa00fe70c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sales", schema=None) as batch_op:
        batch_op.add_column(sa.Column("customer_name", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("customer_phone", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("customer_mobile", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("customer_email", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("customer_city", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("customer_address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("customer_tax_office", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("customer_tax_number", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("customer_note", sa.String(length=200), nullable=True))


def downgrade():
    with op.batch_alter_table("sales", schema=None) as batch_op:
        batch_op.drop_column("customer_note")
        batch_op.drop_column("customer_tax_number")
        batch_op.drop_column("customer_tax_office")
        batch_op.drop_column("customer_address")
        batch_op.drop_column("customer_city")
        batch_op.drop_column("customer_email")
        batch_op.drop_column("customer_mobile")
        batch_op.drop_column("customer_phone")
        batch_op.drop_column("customer_name")
