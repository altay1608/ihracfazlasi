"""add site, store, package, user, role and permission foundation

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-08-19 12:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f7a8b9c0d1e2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


FEATURE_SEED = (
    (1, "dashboard", "Kontrol Merkezi", 10),
    (2, "products", "Ürün ve Stok", 20),
    (3, "inventory_history", "Envanter İşlem Tarihçesi", 30),
    (4, "sales", "Satış İşlemleri", 40),
    (5, "daily_reports", "Günlük Rapor", 50),
    (6, "profit_reports", "Karlılık Analizi", 60),
    (7, "returns", "İade ve Değişim", 70),
    (8, "alerts", "Kritik Stok Uyarıları", 80),
    (9, "inventory_counts", "Stok Sayım Yönetimi", 90),
    (10, "reference_data", "Temel Veri Yönetimi", 100),
    (11, "audit", "Sistem Günlüğü", 110),
    (12, "identity", "Kullanıcı ve Yetki Yönetimi", 120),
    (13, "platform", "Platform Yönetimi", 130),
)


PERMISSION_SEED = (
    (1, "dashboard.access", "Kontrol merkezini görüntüle", "menu", None, "dashboard", 10),
    (49, "dashboard.column.finance", "Ciro, indirim ve kâr göstergelerini görüntüle", "column", "dashboard.access", "dashboard", 11),
    (50, "dashboard.column.stock", "Stok sağlık göstergelerini görüntüle", "column", "dashboard.access", "dashboard", 12),
    (51, "dashboard.column.sales_trend", "Satış performansı ve ürün trendlerini görüntüle", "column", "dashboard.access", "dashboard", 13),
    (2, "products.access", "Ürün ve stok ekranını görüntüle", "menu", None, "products", 20),
    (3, "products.column.purchase_price", "Alış fiyatını görüntüle", "column", "products.access", "products", 21),
    (4, "products.column.purchase_vat", "KDV dahil alış fiyatını görüntüle", "column", "products.access", "products", 22),
    (5, "products.column.sale_net", "KDV hariç satış fiyatını görüntüle", "column", "products.access", "products", 23),
    (6, "products.column.sale_vat", "KDV dahil satış fiyatını görüntüle", "column", "products.access", "products", 24),
    (7, "products.column.stock", "Stok miktarını görüntüle", "column", "products.access", "products", 25),
    (8, "products.action.create", "Ürün oluştur", "action", "products.access", "products", 26),
    (9, "products.action.edit", "Ürün düzenle", "action", "products.access", "products", 27),
    (10, "products.action.delete", "Ürün sil", "action", "products.access", "products", 28),
    (11, "products.action.import", "Excel ile ürün yükle", "action", "products.access", "products", 29),
    (12, "products.action.export", "Ürünleri Excel'e aktar", "action", "products.access", "products", 30),
    (13, "products.action.label", "Etiket yazdır", "action", "products.access", "products", 31),
    (14, "products.action.multiplier", "Perakende çarpanı değiştir", "action", "products.access", "products", 32),
    (15, "products.action.stock", "Stok miktarını elle değiştir", "action", "products.access", "products", 33),
    (16, "inventory_history.access", "Envanter işlem tarihçesini görüntüle", "menu", None, "inventory_history", 40),
    (17, "inventory_history.column.cost", "Envanter hareket maliyetini görüntüle", "column", "inventory_history.access", "inventory_history", 41),
    (18, "sales.access", "Satış yönetimini görüntüle", "menu", None, "sales", 50),
    (19, "sales.action.complete", "Yeni satış tamamla", "action", "sales.access", "sales", 51),
    (20, "sales.action.edit", "Geçmiş satışı yeniden düzenle", "action", "sales.access", "sales", 52),
    (21, "sales.action.receipt", "Satış fişi görüntüle ve yazdır", "action", "sales.access", "sales", 53),
    (22, "sales.customer.view", "Müşteri bilgilerini görüntüle", "column", "sales.access", "sales", 54),
    (23, "daily_reports.access", "Günlük satış raporunu görüntüle", "menu", None, "daily_reports", 60),
    (24, "profit_reports.access", "Karlılık analizini görüntüle", "menu", None, "profit_reports", 70),
    (25, "profit_reports.action.export", "Karlılık analizini Excel'e aktar", "action", "profit_reports.access", "profit_reports", 71),
    (26, "returns.access", "İade ve değişim kayıtlarını görüntüle", "menu", None, "returns", 80),
    (27, "returns.action.create", "İade ve değişim oluştur", "action", "returns.access", "returns", 81),
    (28, "returns.action.receipt", "İade ve değişim fişi yazdır", "action", "returns.access", "returns", 82),
    (29, "alerts.access", "Kritik stok uyarılarını görüntüle", "menu", None, "alerts", 90),
    (30, "alerts.action.manage", "Kritik stok eşiklerini değiştir", "action", "alerts.access", "alerts", 91),
    (31, "inventory_counts.access", "Stok sayımlarını görüntüle", "menu", None, "inventory_counts", 100),
    (32, "inventory_counts.action.create", "Stok sayımı oluştur", "action", "inventory_counts.access", "inventory_counts", 101),
    (33, "inventory_counts.action.scan", "Sayım barkodu okut", "action", "inventory_counts.access", "inventory_counts", 102),
    (34, "inventory_counts.action.save", "Sayım miktarlarını kaydet", "action", "inventory_counts.access", "inventory_counts", 103),
    (35, "inventory_counts.action.approve", "Sayımı onayla ve stoğa uygula", "action", "inventory_counts.access", "inventory_counts", 104),
    (36, "inventory_counts.action.delete", "Sayım kaydını sil", "action", "inventory_counts.access", "inventory_counts", 105),
    (37, "reference_data.access", "Temel veri yönetimini görüntüle", "menu", None, "reference_data", 110),
    (38, "reference_data.action.manage", "Temel verileri değiştir", "action", "reference_data.access", "reference_data", 111),
    (39, "audit.access", "Site sistem günlüğünü görüntüle", "menu", None, "audit", 120),
    (40, "audit.action.manage", "Ekran kayıt tercihlerini değiştir", "action", "audit.access", "audit", 121),
    (41, "identity.access", "Kullanıcı ve yetki yönetimini görüntüle", "menu", None, "identity", 130),
    (42, "identity.action.users", "Kullanıcıları yönet", "action", "identity.access", "identity", 131),
    (43, "identity.action.roles", "Rol ve yetkileri yönet", "action", "identity.access", "identity", 132),
    (44, "identity.action.stores", "Mağazaları yönet", "action", "identity.access", "identity", 133),
    (45, "platform.access", "Platform yönetimini görüntüle", "menu", None, "platform", 140),
    (46, "platform.action.sites", "Siteleri yönet", "action", "platform.access", "platform", 141),
    (47, "platform.action.packages", "Paketleri yönet", "action", "platform.access", "platform", 142),
    (48, "platform.action.security_logs", "Platform güvenlik kayıtlarını görüntüle", "action", "platform.access", "platform", 143),
)


CUSTOMER_REPRESENTATIVE_CODES = {
    "dashboard.access",
    "dashboard.column.stock",
    "dashboard.column.sales_trend",
    "products.access",
    "products.column.sale_vat",
    "products.column.stock",
    "products.action.label",
    "sales.access",
    "sales.action.complete",
    "sales.action.receipt",
    "sales.customer.view",
    "returns.access",
    "returns.action.create",
    "returns.action.receipt",
    "alerts.access",
    "inventory_counts.access",
    "inventory_counts.action.create",
    "inventory_counts.action.scan",
    "inventory_counts.action.save",
}


def upgrade():
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_packages_code"), "packages", ["code"], unique=True)

    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_features_code"), "features", ["code"], unique=True)

    op.create_table(
        "package_features",
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("package_id", "feature_id"),
    )

    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_sandbox", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_sites_code"), "sites", ["code"], unique=True)
    op.create_index(op.f("ix_sites_package_id"), "sites", ["package_id"], unique=False)

    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "code", name="uq_stores_site_code"),
    )
    op.create_index(op.f("ix_stores_site_id"), "stores", ["site_id"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_permissions_code"), "permissions", ["code"], unique=True)
    op.create_index(op.f("ix_permissions_feature_id"), "permissions", ["feature_id"], unique=False)
    op.create_index(op.f("ix_permissions_parent_id"), "permissions", ["parent_id"], unique=False)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "code", name="uq_roles_site_code"),
    )
    op.create_index(op.f("ix_roles_site_id"), "roles", ["site_id"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_platform_superadmin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "user_site_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("all_stores", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "site_id", name="uq_user_site_roles_user_site"),
    )
    op.create_index(op.f("ix_user_site_roles_role_id"), "user_site_roles", ["role_id"], unique=False)
    op.create_index(op.f("ix_user_site_roles_site_id"), "user_site_roles", ["site_id"], unique=False)
    op.create_index(op.f("ix_user_site_roles_user_id"), "user_site_roles", ["user_id"], unique=False)

    op.create_table(
        "user_store_access",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "store_id", name="uq_user_store_access_user_store"),
    )
    op.create_index(op.f("ix_user_store_access_store_id"), "user_store_access", ["store_id"], unique=False)
    op.create_index(op.f("ix_user_store_access_user_id"), "user_store_access", ["user_id"], unique=False)

    connection = op.get_bind()
    packages = sa.table(
        "packages",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_active", sa.Boolean),
    )
    features = sa.table(
        "features",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    sites = sa.table(
        "sites",
        sa.column("id", sa.Integer),
        sa.column("package_id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("is_sandbox", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    stores = sa.table(
        "stores",
        sa.column("id", sa.Integer),
        sa.column("site_id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Integer),
        sa.column("parent_id", sa.Integer),
        sa.column("feature_id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("kind", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    roles = sa.table(
        "roles",
        sa.column("id", sa.Integer),
        sa.column("site_id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("is_system_role", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        packages,
        [
            {"id": 1, "code": "BASIC", "name": "Baz", "description": "Başlangıç paketi", "is_active": True},
            {"id": 2, "code": "STANDARD", "name": "Orta", "description": "Gelişmiş operasyon paketi", "is_active": True},
            {"id": 3, "code": "PRO", "name": "Pro", "description": "Tüm mevcut özellikler", "is_active": True},
        ],
    )
    op.bulk_insert(
        features,
        [{"id": item[0], "code": item[1], "name": item[2], "sort_order": item[3]} for item in FEATURE_SEED],
    )
    package_features = sa.table(
        "package_features",
        sa.column("package_id", sa.Integer),
        sa.column("feature_id", sa.Integer),
    )
    op.bulk_insert(package_features, [{"package_id": 3, "feature_id": item[0]} for item in FEATURE_SEED])
    op.bulk_insert(
        sites,
        [
            {"id": 1, "package_id": 3, "code": "IFG", "name": "İhraç Fazlası Giyim", "is_sandbox": False, "is_active": True},
            {"id": 2, "package_id": 3, "code": "DEV", "name": "Development Sandbox", "is_sandbox": True, "is_active": True},
        ],
    )
    op.bulk_insert(
        stores,
        [
            {"id": 1, "site_id": 1, "code": "MERKEZ", "name": "Merkez Mağaza", "is_active": True},
            {"id": 2, "site_id": 2, "code": "TEST", "name": "Test Mağaza", "is_active": True},
        ],
    )

    feature_ids = {item[1]: item[0] for item in FEATURE_SEED}
    permission_ids = {item[1]: item[0] for item in PERMISSION_SEED}
    op.bulk_insert(
        permissions,
        [
            {
                "id": item[0],
                "code": item[1],
                "name": item[2],
                "kind": item[3],
                "parent_id": permission_ids.get(item[4]),
                "feature_id": feature_ids[item[5]],
                "sort_order": item[6],
            }
            for item in PERMISSION_SEED
        ],
    )
    op.bulk_insert(
        roles,
        [
            {"id": 1, "site_id": 1, "code": "OWNER_MANAGER", "name": "Mağaza Yöneticisi / Sahip", "is_system_role": True, "is_active": True},
            {"id": 2, "site_id": 1, "code": "CUSTOMER_REPRESENTATIVE", "name": "Mağaza Müşteri Temsilcisi", "is_system_role": True, "is_active": True},
            {"id": 3, "site_id": 2, "code": "OWNER_MANAGER", "name": "Mağaza Yöneticisi / Sahip", "is_system_role": True, "is_active": True},
            {"id": 4, "site_id": 2, "code": "CUSTOMER_REPRESENTATIVE", "name": "Mağaza Müşteri Temsilcisi", "is_system_role": True, "is_active": True},
        ],
    )

    site_permission_ids = [item[0] for item in PERMISSION_SEED if item[5] != "platform"]
    representative_permission_ids = [permission_ids[code] for code in CUSTOMER_REPRESENTATIVE_CODES]
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )
    op.bulk_insert(
        role_permissions,
        [
            *({"role_id": role_id, "permission_id": permission_id} for role_id in (1, 3) for permission_id in site_permission_ids),
            *({"role_id": role_id, "permission_id": permission_id} for role_id in (2, 4) for permission_id in representative_permission_ids),
        ],
    )

    if connection.dialect.name == "postgresql":
        for table_name in ("packages", "features", "sites", "stores", "permissions", "roles"):
            connection.execute(
                sa.text(
                    f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)"
                )
            )


def downgrade():
    op.drop_index(op.f("ix_user_store_access_user_id"), table_name="user_store_access")
    op.drop_index(op.f("ix_user_store_access_store_id"), table_name="user_store_access")
    op.drop_table("user_store_access")
    op.drop_index(op.f("ix_user_site_roles_user_id"), table_name="user_site_roles")
    op.drop_index(op.f("ix_user_site_roles_site_id"), table_name="user_site_roles")
    op.drop_index(op.f("ix_user_site_roles_role_id"), table_name="user_site_roles")
    op.drop_table("user_site_roles")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_roles_site_id"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_permissions_parent_id"), table_name="permissions")
    op.drop_index(op.f("ix_permissions_feature_id"), table_name="permissions")
    op.drop_index(op.f("ix_permissions_code"), table_name="permissions")
    op.drop_table("permissions")
    op.drop_index(op.f("ix_stores_site_id"), table_name="stores")
    op.drop_table("stores")
    op.drop_index(op.f("ix_sites_package_id"), table_name="sites")
    op.drop_index(op.f("ix_sites_code"), table_name="sites")
    op.drop_table("sites")
    op.drop_table("package_features")
    op.drop_index(op.f("ix_features_code"), table_name="features")
    op.drop_table("features")
    op.drop_index(op.f("ix_packages_code"), table_name="packages")
    op.drop_table("packages")
