"""add site and store scope to operational data

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-08-19 12:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


SITE_TABLES = (
    "categories",
    "variants",
    "payment_methods",
    "return_reasons",
    "retail_multipliers",
    "products",
)


STORE_SCOPED_TABLES = (
    "product_barcodes",
    "sales",
    "sale_items",
    "returns",
    "return_items",
    "inventory_counts",
    "inventory_count_lines",
    "inventory_transactions",
)


def _add_site_column(table_name):
    with op.batch_alter_table(table_name, schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.add_column(sa.Column("site_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table_name}_site_id_sites",
            "sites",
            ["site_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(f"ix_{table_name}_site_id", ["site_id"], unique=False)


def _add_store_scope(table_name):
    _add_site_column(table_name)
    with op.batch_alter_table(table_name, schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.add_column(sa.Column("store_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table_name}_store_id_stores",
            "stores",
            ["store_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(f"ix_{table_name}_store_id", ["store_id"], unique=False)


def _make_scope_required(table_name, include_store=False):
    with op.batch_alter_table(table_name, schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.alter_column("site_id", existing_type=sa.Integer(), nullable=False)
        if include_store:
            batch_op.alter_column("store_id", existing_type=sa.Integer(), nullable=False)


def _unique_constraint_name(table_name, columns, fallback):
    expected_columns = set(columns)
    inspector = sa.inspect(op.get_bind())
    for constraint in inspector.get_unique_constraints(table_name):
        if set(constraint.get("column_names") or ()) == expected_columns:
            return constraint.get("name") or fallback
    return fallback


def upgrade():
    for table_name in SITE_TABLES:
        _add_site_column(table_name)
    for table_name in STORE_SCOPED_TABLES:
        _add_store_scope(table_name)

    with op.batch_alter_table("audit_logs", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.add_column(sa.Column("site_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("store_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_audit_logs_site_id_sites", "sites", ["site_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_audit_logs_store_id_stores", "stores", ["store_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_audit_logs_user_id_users", "users", ["user_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_audit_logs_site_id", ["site_id"], unique=False)
        batch_op.create_index("ix_audit_logs_store_id", ["store_id"], unique=False)
        batch_op.create_index("ix_audit_logs_user_id", ["user_id"], unique=False)

    connection = op.get_bind()
    for table_name in SITE_TABLES:
        connection.execute(sa.text(f"UPDATE {table_name} SET site_id = 1 WHERE site_id IS NULL"))
    for table_name in STORE_SCOPED_TABLES:
        connection.execute(
            sa.text(f"UPDATE {table_name} SET site_id = 1, store_id = 1 WHERE site_id IS NULL OR store_id IS NULL")
        )
    connection.execute(sa.text("UPDATE audit_logs SET site_id = 1, store_id = 1 WHERE site_id IS NULL"))

    for table_name in SITE_TABLES:
        _make_scope_required(table_name)
    for table_name in STORE_SCOPED_TABLES:
        _make_scope_required(table_name, include_store=True)

    with op.batch_alter_table("categories", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_index("ix_categories_name")
        batch_op.create_index("ix_categories_name", ["name"], unique=False)
        batch_op.create_unique_constraint("uq_categories_site_name", ["site_id", "name"])
    with op.batch_alter_table("variants", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_index("ix_variants_name")
        batch_op.create_index("ix_variants_name", ["name"], unique=False)
        batch_op.create_unique_constraint("uq_variants_site_name", ["site_id", "name"])
    with op.batch_alter_table("payment_methods", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_index("ix_payment_methods_name")
        batch_op.create_index("ix_payment_methods_name", ["name"], unique=False)
        batch_op.create_unique_constraint("uq_payment_methods_site_name", ["site_id", "name"])
    with op.batch_alter_table("return_reasons", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_index("ix_return_reasons_name")
        batch_op.create_index("ix_return_reasons_name", ["name"], unique=False)
        batch_op.create_unique_constraint("uq_return_reasons_site_name", ["site_id", "name"])
    retail_multiplier_name_uq = _unique_constraint_name(
        "retail_multipliers",
        ["name"],
        "uq_retail_multipliers_name",
    )
    with op.batch_alter_table("retail_multipliers", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(retail_multiplier_name_uq, type_="unique")
        batch_op.drop_index("ix_retail_multipliers_name")
        batch_op.create_index("ix_retail_multipliers_name", ["name"], unique=False)
        batch_op.create_unique_constraint("uq_retail_multipliers_site_name", ["site_id", "name"])
    product_barcode_uq = _unique_constraint_name("products", ["barcode"], "uq_products_barcode")
    with op.batch_alter_table("products", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(product_barcode_uq, type_="unique")
        batch_op.drop_index("ix_products_barcode")
        batch_op.drop_index("ix_products_product_code")
        batch_op.create_index("ix_products_barcode", ["barcode"], unique=False)
        batch_op.create_index("ix_products_product_code", ["product_code"], unique=False)
        batch_op.create_unique_constraint("uq_products_site_barcode", ["site_id", "barcode"])
        batch_op.create_unique_constraint("uq_products_site_product_code", ["site_id", "product_code"])
    unit_barcode_uq = _unique_constraint_name(
        "product_barcodes",
        ["barcode"],
        "uq_product_barcodes_barcode",
    )
    with op.batch_alter_table("product_barcodes", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(unit_barcode_uq, type_="unique")
        batch_op.drop_index("ix_product_barcodes_barcode")
        batch_op.create_index("ix_product_barcodes_barcode", ["barcode"], unique=False)
        batch_op.create_unique_constraint("uq_product_barcodes_site_barcode", ["site_id", "barcode"])

    op.create_table(
        "store_inventories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("critical_stock_level", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "product_id", name="uq_store_inventories_store_product"),
    )
    op.create_index("ix_store_inventories_site_id", "store_inventories", ["site_id"], unique=False)
    op.create_index("ix_store_inventories_store_id", "store_inventories", ["store_id"], unique=False)
    op.create_index("ix_store_inventories_product_id", "store_inventories", ["product_id"], unique=False)
    connection.execute(
        sa.text(
            """
            INSERT INTO store_inventories
                (site_id, store_id, product_id, stock_quantity, critical_stock_level)
            SELECT site_id, 1, id, stock_quantity, critical_stock_level
            FROM products
            """
        )
    )


def downgrade():
    op.drop_index("ix_store_inventories_product_id", table_name="store_inventories")
    op.drop_index("ix_store_inventories_store_id", table_name="store_inventories")
    op.drop_index("ix_store_inventories_site_id", table_name="store_inventories")
    op.drop_table("store_inventories")

    with op.batch_alter_table("product_barcodes", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint("uq_product_barcodes_site_barcode", type_="unique")
        batch_op.drop_index("ix_product_barcodes_barcode")
        batch_op.create_index("ix_product_barcodes_barcode", ["barcode"], unique=True)
        batch_op.create_unique_constraint("uq_product_barcodes_barcode", ["barcode"])
    with op.batch_alter_table("products", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint("uq_products_site_product_code", type_="unique")
        batch_op.drop_constraint("uq_products_site_barcode", type_="unique")
        batch_op.drop_index("ix_products_product_code")
        batch_op.drop_index("ix_products_barcode")
        batch_op.create_index("ix_products_product_code", ["product_code"], unique=True)
        batch_op.create_index("ix_products_barcode", ["barcode"], unique=True)
        batch_op.create_unique_constraint("uq_products_barcode", ["barcode"])

    for table_name in ("retail_multipliers", "return_reasons", "payment_methods", "variants", "categories"):
        composite_name = f"uq_{table_name}_site_name"
        index_name = f"ix_{table_name}_name"
        with op.batch_alter_table(table_name, schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
            batch_op.drop_constraint(composite_name, type_="unique")
            batch_op.drop_index(index_name)
            batch_op.create_index(index_name, ["name"], unique=True)
            if table_name == "retail_multipliers":
                batch_op.create_unique_constraint("uq_retail_multipliers_name", ["name"])

    with op.batch_alter_table("audit_logs", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_index("ix_audit_logs_user_id")
        batch_op.drop_index("ix_audit_logs_store_id")
        batch_op.drop_index("ix_audit_logs_site_id")
        batch_op.drop_constraint("fk_audit_logs_user_id_users", type_="foreignkey")
        batch_op.drop_constraint("fk_audit_logs_store_id_stores", type_="foreignkey")
        batch_op.drop_constraint("fk_audit_logs_site_id_sites", type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.drop_column("store_id")
        batch_op.drop_column("site_id")

    for table_name in reversed(STORE_SCOPED_TABLES):
        with op.batch_alter_table(table_name, schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_store_id")
            batch_op.drop_constraint(f"fk_{table_name}_store_id_stores", type_="foreignkey")
            batch_op.drop_column("store_id")
            batch_op.drop_index(f"ix_{table_name}_site_id")
            batch_op.drop_constraint(f"fk_{table_name}_site_id_sites", type_="foreignkey")
            batch_op.drop_column("site_id")
    for table_name in reversed(SITE_TABLES):
        with op.batch_alter_table(table_name, schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_site_id")
            batch_op.drop_constraint(f"fk_{table_name}_site_id_sites", type_="foreignkey")
            batch_op.drop_column("site_id")
