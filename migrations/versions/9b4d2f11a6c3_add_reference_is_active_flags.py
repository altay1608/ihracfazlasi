"""add is_active flags to reference tables

Revision ID: 9b4d2f11a6c3
Revises: f2b7d3c4a9e2
Create Date: 2026-04-05 23:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "9b4d2f11a6c3"
down_revision = "f2b7d3c4a9e2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    with op.batch_alter_table("variants", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    with op.batch_alter_table("retail_multipliers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    with op.batch_alter_table("return_reasons", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table("return_reasons", schema=None) as batch_op:
        batch_op.drop_column("is_active")

    with op.batch_alter_table("retail_multipliers", schema=None) as batch_op:
        batch_op.drop_column("is_active")

    with op.batch_alter_table("variants", schema=None) as batch_op:
        batch_op.drop_column("is_active")

    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_column("is_active")
