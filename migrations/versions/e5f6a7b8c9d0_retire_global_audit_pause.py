"""retire legacy global audit pause setting

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-19 00:10:00.000000
"""

from alembic import op


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    # Earlier builds exposed a global UI pause. Screen-level settings replace it.
    op.execute(
        "UPDATE system_settings SET value = '1' WHERE key = 'audit_logging_enabled'"
    )


def downgrade():
    pass
