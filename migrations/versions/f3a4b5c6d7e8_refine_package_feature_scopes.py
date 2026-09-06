"""refine package feature scopes

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-08-20 09:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


BASIC_FEATURES = (
    "dashboard",
    "products",
    "inventory_history",
    "sales",
    "daily_reports",
    "returns",
    "reference_data",
)
STANDARD_FEATURES = BASIC_FEATURES + (
    "alerts",
    "inventory_counts",
)
PRO_FEATURES = STANDARD_FEATURES + (
    "profit_reports",
    "audit",
    "identity",
)

LEGACY_BASIC_FEATURES = STANDARD_FEATURES
LEGACY_STANDARD_FEATURES = LEGACY_BASIC_FEATURES + (
    "profit_reports",
    "audit",
    "identity",
)


def _set_package_features(connection, package_code, feature_codes):
    package_id = connection.execute(
        sa.text("SELECT id FROM packages WHERE code = :code"),
        {"code": package_code},
    ).scalar_one_or_none()
    if package_id is None:
        return

    connection.execute(
        sa.text("DELETE FROM package_features WHERE package_id = :package_id"),
        {"package_id": package_id},
    )
    if not feature_codes:
        return

    feature_ids = connection.execute(
        sa.text("SELECT id FROM features WHERE code IN :codes").bindparams(
            sa.bindparam("codes", expanding=True)
        ),
        {"codes": tuple(feature_codes)},
    ).scalars().all()
    for feature_id in feature_ids:
        connection.execute(
            sa.text(
                "INSERT INTO package_features (package_id, feature_id) "
                "VALUES (:package_id, :feature_id)"
            ),
            {"package_id": package_id, "feature_id": feature_id},
        )


def upgrade():
    connection = op.get_bind()
    _set_package_features(connection, "BASIC", BASIC_FEATURES)
    _set_package_features(connection, "STANDARD", STANDARD_FEATURES)
    _set_package_features(connection, "PRO", PRO_FEATURES)


def downgrade():
    connection = op.get_bind()
    all_features = connection.execute(sa.text("SELECT code FROM features")).scalars().all()
    _set_package_features(connection, "BASIC", LEGACY_BASIC_FEATURES)
    _set_package_features(connection, "STANDARD", LEGACY_STANDARD_FEATURES)
    _set_package_features(connection, "PRO", tuple(all_features))
