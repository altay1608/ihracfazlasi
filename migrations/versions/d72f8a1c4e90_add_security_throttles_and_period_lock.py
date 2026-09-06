"""add security throttles and finance period lock

Revision ID: d72f8a1c4e90
Revises: 4a02abf54669
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa


revision = "d72f8a1c4e90"
down_revision = "4a02abf54669"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_throttles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("first_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_throttles_key_hash", "auth_throttles", ["key_hash"], unique=True)
    op.create_index("ix_auth_throttles_locked_until", "auth_throttles", ["locked_until"], unique=False)

    with op.batch_alter_table("daily_cash_closings") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(length=20), server_default="closed", nullable=False))
        batch_op.add_column(sa.Column("reopened_by_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("reopened_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("reopen_reason", sa.String(length=500), nullable=True))
        batch_op.create_check_constraint("ck_daily_closing_status", "status IN ('closed','reopened')")
        batch_op.create_foreign_key(
            "fk_daily_cash_closings_reopened_by_user_id_users",
            "users",
            ["reopened_by_user_id"],
            ["id"],
        )
        batch_op.create_index("ix_daily_cash_closings_status", ["status"], unique=False)


def downgrade():
    with op.batch_alter_table("daily_cash_closings") as batch_op:
        batch_op.drop_index("ix_daily_cash_closings_status")
        batch_op.drop_constraint("fk_daily_cash_closings_reopened_by_user_id_users", type_="foreignkey")
        batch_op.drop_constraint("ck_daily_closing_status", type_="check")
        batch_op.drop_column("reopen_reason")
        batch_op.drop_column("reopened_at")
        batch_op.drop_column("reopened_by_user_id")
        batch_op.drop_column("status")

    op.drop_index("ix_auth_throttles_locked_until", table_name="auth_throttles")
    op.drop_index("ix_auth_throttles_key_hash", table_name="auth_throttles")
    op.drop_table("auth_throttles")
