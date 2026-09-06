"""add dashboard data permissions

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-08-19 14:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


PERMISSIONS = (
    ("dashboard.column.finance", "Ciro, indirim ve kâr göstergelerini görüntüle", 11),
    ("dashboard.column.stock", "Stok sağlık göstergelerini görüntüle", 12),
    ("dashboard.column.sales_trend", "Satış performansı ve ürün trendlerini görüntüle", 13),
)


def upgrade():
    connection = op.get_bind()
    feature_id = connection.execute(
        sa.text("SELECT id FROM features WHERE code = :code"),
        {"code": "dashboard"},
    ).scalar_one()
    parent_id = connection.execute(
        sa.text("SELECT id FROM permissions WHERE code = :code"),
        {"code": "dashboard.access"},
    ).scalar_one()

    for code, name, sort_order in PERMISSIONS:
        exists = connection.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"),
            {"code": code},
        ).scalar_one_or_none()
        if exists is None:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO permissions (parent_id, feature_id, code, name, kind, sort_order)
                    VALUES (:parent_id, :feature_id, :code, :name, 'column', :sort_order)
                    """
                ),
                {
                    "parent_id": parent_id,
                    "feature_id": feature_id,
                    "code": code,
                    "name": name,
                    "sort_order": sort_order,
                },
            )

    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT roles.id, permissions.id
            FROM roles
            JOIN permissions ON permissions.code IN (
                'dashboard.column.finance',
                'dashboard.column.stock',
                'dashboard.column.sales_trend'
            )
            WHERE roles.code = 'OWNER_MANAGER'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions existing
                  WHERE existing.role_id = roles.id
                    AND existing.permission_id = permissions.id
              )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT roles.id, permissions.id
            FROM roles
            JOIN permissions ON permissions.code IN (
                'dashboard.column.stock',
                'dashboard.column.sales_trend'
            )
            WHERE roles.code = 'CUSTOMER_REPRESENTATIVE'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions existing
                  WHERE existing.role_id = roles.id
                    AND existing.permission_id = permissions.id
              )
            """
        )
    )


def downgrade():
    connection = op.get_bind()
    codes = tuple(item[0] for item in PERMISSIONS)
    permission_ids = [
        row[0]
        for row in connection.execute(
            sa.text(
                """
                SELECT id FROM permissions
                WHERE code IN (
                    'dashboard.column.finance',
                    'dashboard.column.stock',
                    'dashboard.column.sales_trend'
                )
                """
            )
        ).all()
    ]
    if permission_ids:
        connection.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": permission_ids},
        )
        connection.execute(
            sa.text("DELETE FROM permissions WHERE code IN :codes").bindparams(
                sa.bindparam("codes", expanding=True)
            ),
            {"codes": codes},
        )
