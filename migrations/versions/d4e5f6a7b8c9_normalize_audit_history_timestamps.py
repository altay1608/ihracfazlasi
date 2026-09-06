"""normalize audit and inventory history timestamps for Istanbul

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-18 23:30:00.000000
"""

from alembic import op


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "postgresql":
        op.execute("UPDATE audit_logs SET occurred_at = occurred_at + INTERVAL '3 hours'")
        op.execute(
            """
            UPDATE inventory_transactions
            SET occurred_at = occurred_at + INTERVAL '3 hours',
                created_at = created_at + INTERVAL '3 hours'
            WHERE transaction_code <> 'OPENING-BAL'
            """
        )
    elif dialect_name == "sqlite":
        op.execute("UPDATE audit_logs SET occurred_at = datetime(occurred_at, '+3 hours')")
        op.execute(
            """
            UPDATE inventory_transactions
            SET occurred_at = datetime(occurred_at, '+3 hours'),
                created_at = datetime(created_at, '+3 hours')
            WHERE transaction_code <> 'OPENING-BAL'
            """
        )


def downgrade():
    # Timestamp normalization is intentionally not reversed.
    pass
