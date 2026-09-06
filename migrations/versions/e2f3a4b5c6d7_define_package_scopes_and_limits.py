"""define package scopes and limits

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-08-19 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


BASIC_FEATURES = (
    "dashboard",
    "products",
    "inventory_history",
    "sales",
    "daily_reports",
    "returns",
    "alerts",
    "inventory_counts",
    "reference_data",
)
STANDARD_FEATURES = BASIC_FEATURES + ("profit_reports", "audit", "identity")


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
    with op.batch_alter_table("packages") as batch_op:
        batch_op.add_column(sa.Column("max_stores", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("max_users", sa.Integer(), nullable=True))

    connection = op.get_bind()
    limits = {
        "BASIC": (1, 2),
        "STANDARD": (3, 8),
        "PRO": (10, 25),
    }
    for code, (max_stores, max_users) in limits.items():
        connection.execute(
            sa.text(
                "UPDATE packages SET max_stores = :max_stores, max_users = :max_users "
                "WHERE code = :code"
            ),
            {"code": code, "max_stores": max_stores, "max_users": max_users},
        )
    connection.execute(sa.text("UPDATE packages SET max_stores = 1 WHERE max_stores IS NULL"))
    connection.execute(sa.text("UPDATE packages SET max_users = 2 WHERE max_users IS NULL"))

    with op.batch_alter_table("packages") as batch_op:
        batch_op.alter_column("max_stores", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("max_users", existing_type=sa.Integer(), nullable=False)

    all_features = connection.execute(sa.text("SELECT code FROM features")).scalars().all()
    _set_package_features(connection, "BASIC", BASIC_FEATURES)
    _set_package_features(connection, "STANDARD", STANDARD_FEATURES)
    _set_package_features(connection, "PRO", tuple(all_features))


def downgrade():
    connection = op.get_bind()
    all_features = connection.execute(sa.text("SELECT code FROM features")).scalars().all()
    _set_package_features(connection, "BASIC", ())
    _set_package_features(connection, "STANDARD", ())
    _set_package_features(connection, "PRO", tuple(all_features))
    with op.batch_alter_table("packages") as batch_op:
        batch_op.drop_column("max_users")
        batch_op.drop_column("max_stores")
