"""add return note

Revision ID: d1a7f4b2c9e1
Revises: b9c4d7f13b2d
Create Date: 2026-03-30 21:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1a7f4b2c9e1"
down_revision = "b9c4d7f13b2d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("returns", schema=None) as batch_op:
        batch_op.add_column(sa.Column("note", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("returns", schema=None) as batch_op:
        batch_op.drop_column("note")
