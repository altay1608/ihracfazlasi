"""add user two factor authentication

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-08-19 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("two_factor_secret", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("two_factor_confirmed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("two_factor_recovery_codes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("two_factor_last_counter", sa.BigInteger(), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("two_factor_last_counter")
        batch_op.drop_column("two_factor_recovery_codes")
        batch_op.drop_column("two_factor_confirmed_at")
        batch_op.drop_column("two_factor_enabled")
        batch_op.drop_column("two_factor_secret")
