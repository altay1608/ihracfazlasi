"""add lossless customer order header and line foundation

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-08-24 12:00:00.000000
"""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from alembic import op
import sqlalchemy as sa


revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None

MONEY = Decimal("0.01")
VAT_MULTIPLIER = Decimal("1.10")


def money(value):
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def allocate(total, weighted_rows):
    total = money(total)
    weight_total = sum((max(money(weight), Decimal("0.00")) for _, weight in weighted_rows), Decimal("0.00"))
    remaining = total
    result = {}
    for index, (line_id, raw_weight) in enumerate(weighted_rows):
        weight = max(money(raw_weight), Decimal("0.00"))
        if index == len(weighted_rows) - 1:
            amount = remaining
        elif weight_total:
            amount = min(money((weight / weight_total) * total), remaining)
        else:
            amount = Decimal("0.00")
        result[line_id] = amount
        remaining = money(remaining - amount)
    return result


def upgrade():
    with op.batch_alter_table("sales") as batch_op:
        batch_op.add_column(sa.Column("order_status", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("payment_status", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("currency_code", sa.String(length=3), nullable=True))
        batch_op.add_column(sa.Column("revision_no", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.add_column(sa.Column("line_no", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("release_no", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("line_status", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("delivered_quantity", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("returned_quantity", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cancelled_quantity", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("header_discount_amount", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("rounding_adjustment_amount", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("vat_rate", sa.Numeric(5, 2), nullable=True))
        batch_op.add_column(sa.Column("unit_cost_snapshot", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("product_code_snapshot", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("product_name_snapshot", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("product_variant_snapshot", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("product_category_snapshot", sa.String(length=100), nullable=True))

    with op.batch_alter_table("return_items") as batch_op:
        batch_op.add_column(sa.Column("original_sale_item_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_return_items_original_sale_item_id_sale_items",
            "sale_items",
            ["original_sale_item_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_return_items_original_sale_item_id",
            ["original_sale_item_id"],
            unique=False,
        )

    connection = op.get_bind()
    sales = connection.execute(
        sa.text(
            "SELECT id, sale_date, total_amount, total_discount, created_at "
            "FROM sales ORDER BY id"
        )
    ).mappings().all()
    products = {
        row["id"]: row
        for row in connection.execute(
            sa.text(
                "SELECT id, product_code, name, variant, category, purchase_price "
                "FROM products"
            )
        ).mappings()
    }
    lines_by_sale = defaultdict(list)
    for row in connection.execute(
        sa.text(
            "SELECT id, sale_id, product_id, quantity, unit_price, discount_amount "
            "FROM sale_items ORDER BY sale_id, id"
        )
    ).mappings():
        lines_by_sale[row["sale_id"]].append(row)

    returned_by_line = defaultdict(int)
    positive_return_rows = connection.execute(
        sa.text(
            "SELECT ri.id, ri.product_id, ri.quantity, r.original_sale_id "
            "FROM return_items ri JOIN returns r ON r.id = ri.return_id "
            "WHERE ri.refund_amount > 0 ORDER BY ri.id"
        )
    ).mappings().all()
    for return_row in positive_return_rows:
        candidates = [
            line
            for line in lines_by_sale.get(return_row["original_sale_id"], [])
            if line["product_id"] == return_row["product_id"]
        ]
        if len(candidates) != 1:
            raise RuntimeError(
                "Kayıpsız iade-satır eşlemesi yapılamadı: "
                f"return_item={return_row['id']} candidate_count={len(candidates)}"
            )
        line_id = candidates[0]["id"]
        returned_by_line[line_id] += int(return_row["quantity"] or 0)
        connection.execute(
            sa.text(
                "UPDATE return_items SET original_sale_item_id=:line_id WHERE id=:return_item_id"
            ),
            {"line_id": line_id, "return_item_id": return_row["id"]},
        )

    for sale in sales:
        lines = lines_by_sale.get(sale["id"], [])
        line_discount_total = sum((money(line["discount_amount"]) for line in lines), Decimal("0.00"))
        header_discount = max(money(sale["total_discount"]) - line_discount_total, Decimal("0.00"))
        weighted_lines = [
            (
                line["id"],
                money(money(line["unit_price"]) * int(line["quantity"] or 0) - money(line["discount_amount"])),
            )
            for line in lines
        ]
        header_allocations = allocate(header_discount, weighted_lines)
        gross_without_rounding = Decimal("0.00")
        delivered_total = 0
        returned_total = 0

        for line_no, line in enumerate(lines, start=1):
            product = products.get(line["product_id"])
            if product is None:
                raise RuntimeError(f"Satış satırının ürün kaydı bulunamadı: sale_item={line['id']}")
            delivered = int(line["quantity"] or 0)
            returned = returned_by_line.get(line["id"], 0)
            if returned > delivered:
                raise RuntimeError(
                    f"İade adedi teslim adedini aşıyor: sale_item={line['id']} returned={returned} delivered={delivered}"
                )
            if returned == 0:
                line_status = "DELIVERED"
            elif returned == delivered:
                line_status = "RETURNED"
            else:
                line_status = "PARTIALLY_RETURNED"

            line_base = money(
                money(line["unit_price"]) * delivered - money(line["discount_amount"])
            )
            header_share = header_allocations.get(line["id"], Decimal("0.00"))
            line_gross = money((line_base - header_share) * VAT_MULTIPLIER)
            gross_without_rounding += line_gross
            delivered_total += delivered
            returned_total += returned

            connection.execute(
                sa.text(
                    "UPDATE sale_items SET line_no=:line_no, release_no=1, line_status=:line_status, "
                    "delivered_quantity=:delivered, returned_quantity=:returned, cancelled_quantity=0, "
                    "header_discount_amount=:header_discount, rounding_adjustment_amount=0, vat_rate=10, "
                    "unit_cost_snapshot=:unit_cost, product_code_snapshot=:product_code, "
                    "product_name_snapshot=:product_name, product_variant_snapshot=:product_variant, "
                    "product_category_snapshot=:product_category WHERE id=:line_id"
                ),
                {
                    "line_no": line_no,
                    "line_status": line_status,
                    "delivered": delivered,
                    "returned": returned,
                    "header_discount": str(header_share),
                    "unit_cost": str(money(product["purchase_price"])),
                    "product_code": product["product_code"],
                    "product_name": product["name"],
                    "product_variant": product["variant"],
                    "product_category": product["category"],
                    "line_id": line["id"],
                },
            )

        if lines:
            rounding_adjustment = money(money(sale["total_amount"]) - gross_without_rounding)
            if money(gross_without_rounding + rounding_adjustment) != money(sale["total_amount"]):
                raise RuntimeError(f"Sipariş toplamı satırlara mutabık dağıtılamadı: sale={sale['id']}")
            connection.execute(
                sa.text(
                    "UPDATE sale_items SET rounding_adjustment_amount=:adjustment "
                    "WHERE id=:line_id"
                ),
                {"adjustment": str(rounding_adjustment), "line_id": lines[-1]["id"]},
            )

        if returned_total <= 0:
            order_status, payment_status = "DELIVERED", "PAID"
        elif returned_total >= delivered_total:
            order_status, payment_status = "RETURNED", "REFUNDED"
        else:
            order_status, payment_status = "PARTIALLY_RETURNED", "PARTIALLY_REFUNDED"
        connection.execute(
            sa.text(
                "UPDATE sales SET order_status=:order_status, payment_status=:payment_status, "
                "currency_code='TRY', revision_no=1, completed_at=sale_date, "
                "updated_at=COALESCE(created_at, sale_date) WHERE id=:sale_id"
            ),
            {
                "order_status": order_status,
                "payment_status": payment_status,
                "sale_id": sale["id"],
            },
        )

    with op.batch_alter_table("sales") as batch_op:
        batch_op.alter_column("order_status", existing_type=sa.String(length=30), nullable=False)
        batch_op.alter_column("payment_status", existing_type=sa.String(length=30), nullable=False)
        batch_op.alter_column("currency_code", existing_type=sa.String(length=3), nullable=False)
        batch_op.alter_column("revision_no", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("updated_at", existing_type=sa.DateTime(), nullable=False)
        batch_op.create_index("ix_sales_order_status", ["order_status"], unique=False)
        batch_op.create_index("ix_sales_payment_status", ["payment_status"], unique=False)

    with op.batch_alter_table("sale_items") as batch_op:
        for column_name, column_type in (
            ("line_no", sa.Integer()),
            ("release_no", sa.Integer()),
            ("line_status", sa.String(length=30)),
            ("delivered_quantity", sa.Integer()),
            ("returned_quantity", sa.Integer()),
            ("cancelled_quantity", sa.Integer()),
            ("header_discount_amount", sa.Numeric(10, 2)),
            ("rounding_adjustment_amount", sa.Numeric(10, 2)),
            ("vat_rate", sa.Numeric(5, 2)),
            ("unit_cost_snapshot", sa.Numeric(10, 2)),
            ("product_code_snapshot", sa.String(length=32)),
            ("product_name_snapshot", sa.String(length=150)),
            ("product_category_snapshot", sa.String(length=100)),
        ):
            batch_op.alter_column(column_name, existing_type=column_type, nullable=False)
        batch_op.create_index("ix_sale_items_line_status", ["line_status"], unique=False)
        batch_op.create_unique_constraint(
            "uq_sale_items_order_line_release",
            ["sale_id", "line_no", "release_no"],
        )


def downgrade():
    with op.batch_alter_table("return_items") as batch_op:
        batch_op.drop_index("ix_return_items_original_sale_item_id")
        batch_op.drop_constraint(
            "fk_return_items_original_sale_item_id_sale_items",
            type_="foreignkey",
        )
        batch_op.drop_column("original_sale_item_id")

    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.drop_constraint("uq_sale_items_order_line_release", type_="unique")
        batch_op.drop_index("ix_sale_items_line_status")
        for column_name in (
            "product_category_snapshot",
            "product_variant_snapshot",
            "product_name_snapshot",
            "product_code_snapshot",
            "unit_cost_snapshot",
            "vat_rate",
            "rounding_adjustment_amount",
            "header_discount_amount",
            "cancelled_quantity",
            "returned_quantity",
            "delivered_quantity",
            "line_status",
            "release_no",
            "line_no",
        ):
            batch_op.drop_column(column_name)

    with op.batch_alter_table("sales") as batch_op:
        batch_op.drop_index("ix_sales_payment_status")
        batch_op.drop_index("ix_sales_order_status")
        for column_name in (
            "updated_at",
            "completed_at",
            "revision_no",
            "currency_code",
            "payment_status",
            "order_status",
        ):
            batch_op.drop_column(column_name)
