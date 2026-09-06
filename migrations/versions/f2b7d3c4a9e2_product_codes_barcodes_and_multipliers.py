"""product codes, barcodes and retail multipliers

Revision ID: f2b7d3c4a9e2
Revises: d1a7f4b2c9e1
Create Date: 2026-04-05 20:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f2b7d3c4a9e2"
down_revision = "d1a7f4b2c9e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "retail_multipliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("multiplier", sa.Numeric(10, 2), nullable=False, server_default="1.00"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_retail_multipliers_name"), "retail_multipliers", ["name"], unique=True)

    op.execute(
        """
        INSERT INTO retail_multipliers (name, multiplier, is_default)
        VALUES
            ('Standart 1.80x', 1.80, TRUE),
            ('Premium 2.00x', 2.00, FALSE),
            ('Luxury 2.25x', 2.25, FALSE)
        """
    )

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("product_code", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("retail_multiplier_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_products_product_code"), ["product_code"], unique=True)
        batch_op.create_foreign_key(
            "fk_products_retail_multiplier_id",
            "retail_multipliers",
            ["retail_multiplier_id"],
            ["id"],
        )

    connection = op.get_bind()
    default_multiplier_id = connection.execute(
        sa.text("SELECT id FROM retail_multipliers WHERE is_default = TRUE LIMIT 1")
    ).scalar_one()
    products_for_update = connection.execute(sa.text("SELECT id FROM products ORDER BY id ASC")).fetchall()
    update_product = sa.text(
        """
        UPDATE products
        SET product_code = :product_code,
            retail_multiplier_id = :retail_multiplier_id,
            barcode = :barcode
        WHERE id = :id
        """
    )
    for product_id, in products_for_update:
        product_code = f"{int(product_id) + 100000000000:012d}"
        connection.execute(
            update_product,
            {
                "id": product_id,
                "product_code": product_code,
                "retail_multiplier_id": default_multiplier_id,
                "barcode": product_code,
            },
        )

    op.create_table(
        "product_barcodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sale_item_id", sa.Integer(), nullable=True),
        sa.Column("barcode", sa.String(length=64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="available"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["sale_item_id"], ["sale_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode", name="uq_product_barcodes_barcode"),
        sa.UniqueConstraint("product_id", "sequence_no", name="uq_product_barcodes_product_sequence"),
    )
    op.create_index(op.f("ix_product_barcodes_barcode"), "product_barcodes", ["barcode"], unique=True)
    op.create_index(op.f("ix_product_barcodes_product_id"), "product_barcodes", ["product_id"], unique=False)
    op.create_index(op.f("ix_product_barcodes_sale_item_id"), "product_barcodes", ["sale_item_id"], unique=False)
    op.create_index(op.f("ix_product_barcodes_status"), "product_barcodes", ["status"], unique=False)

    products = connection.execute(sa.text("SELECT id, product_code, stock_quantity FROM products ORDER BY id ASC")).fetchall()
    insert_sql = sa.text(
        """
        INSERT INTO product_barcodes (product_id, barcode, sequence_no, status)
        VALUES (:product_id, :barcode, :sequence_no, 'available')
        """
    )
    for product_id, product_code, stock_quantity in products:
        quantity = max(int(stock_quantity or 0), 0)
        for index in range(1, quantity + 1):
            connection.execute(
                insert_sql,
                {
                    "product_id": product_id,
                    "barcode": f"{product_code}-{index:02d}",
                    "sequence_no": index,
                },
            )

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column("product_code", existing_type=sa.String(length=32), nullable=False)


def downgrade():
    op.drop_index(op.f("ix_product_barcodes_status"), table_name="product_barcodes")
    op.drop_index(op.f("ix_product_barcodes_sale_item_id"), table_name="product_barcodes")
    op.drop_index(op.f("ix_product_barcodes_product_id"), table_name="product_barcodes")
    op.drop_index(op.f("ix_product_barcodes_barcode"), table_name="product_barcodes")
    op.drop_table("product_barcodes")

    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_constraint("fk_products_retail_multiplier_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_products_product_code"))
        batch_op.drop_column("retail_multiplier_id")
        batch_op.drop_column("product_code")

    op.drop_index(op.f("ix_retail_multipliers_name"), table_name="retail_multipliers")
    op.drop_table("retail_multipliers")
