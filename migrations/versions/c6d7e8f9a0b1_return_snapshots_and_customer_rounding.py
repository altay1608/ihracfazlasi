"""add return snapshots and reconcile customer-facing line rounding

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-08-24 16:30:00.000000
"""

from collections import defaultdict
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

from alembic import op
import sqlalchemy as sa


revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None

MONEY = Decimal("0.01")
VAT_MULTIPLIER = Decimal("1.10")
ROUNDING_STEP = Decimal("10")
ROUNDING_MIDPOINT = Decimal("5")


def money(value):
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def round_customer_price(value):
    amount = money(value)
    whole_lira = amount.quantize(Decimal("1"), rounding=ROUND_FLOOR)
    cents = amount - whole_lira
    lower_ten = (whole_lira // ROUNDING_STEP) * ROUNDING_STEP
    midpoint = lower_ten + ROUNDING_MIDPOINT
    if cents == 0 and whole_lira == midpoint:
        return money(midpoint)
    if amount <= midpoint:
        return money(lower_ten)
    return money(lower_ten + ROUNDING_STEP)


def allocate_customer_total(total, weighted_rows):
    total = max(money(total), Decimal("0.00"))
    weights = [max(money(weight), Decimal("0.00")) for _, weight in weighted_rows]
    remaining_total = total
    remaining_weight = sum(weights, Decimal("0.00"))
    allocations = {}
    for index, ((row_id, _), weight) in enumerate(zip(weighted_rows, weights)):
        if index == len(weighted_rows) - 1:
            allocation = remaining_total
        elif remaining_weight:
            allocation = min(
                round_customer_price((weight / remaining_weight) * remaining_total),
                remaining_total,
            )
        else:
            allocation = Decimal("0.00")
        allocations[row_id] = money(allocation)
        remaining_total = money(remaining_total - allocation)
        remaining_weight = money(remaining_weight - weight)
    return allocations


def allocate_unit_amounts(total, quantity):
    quantity = int(quantity or 0)
    if quantity <= 0:
        return []
    total_cents = int(money(total) * 100)
    sign = -1 if total_cents < 0 else 1
    base_cents, remainder = divmod(abs(total_cents), quantity)
    return [
        Decimal(sign * (base_cents + (1 if index < remainder else 0))) / Decimal("100")
        for index in range(quantity)
    ]


def upgrade():
    with op.batch_alter_table("return_items") as batch_op:
        batch_op.add_column(sa.Column("gross_refund_amount", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("unit_cost_snapshot", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("product_code_snapshot", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("product_name_snapshot", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("product_variant_snapshot", sa.String(length=120), nullable=True))

    connection = op.get_bind()
    products = {
        row["id"]: row
        for row in connection.execute(
            sa.text(
                "SELECT id, product_code, name, variant, purchase_price FROM products"
            )
        ).mappings()
    }

    lines_by_sale = defaultdict(list)
    line_lookup = {}
    for row in connection.execute(
        sa.text(
            "SELECT id, sale_id, product_id, quantity, delivered_quantity, unit_price, "
            "discount_amount, header_discount_amount, vat_rate, unit_cost_snapshot, "
            "product_code_snapshot, product_name_snapshot, product_variant_snapshot "
            "FROM sale_items ORDER BY sale_id, line_no, release_no"
        )
    ).mappings():
        lines_by_sale[row["sale_id"]].append(row)
        line_lookup[row["id"]] = row

    sales = connection.execute(
        sa.text("SELECT id, total_amount FROM sales ORDER BY id")
    ).mappings().all()
    line_customer_gross = {}
    for sale in sales:
        weighted_rows = []
        for line in lines_by_sale.get(sale["id"], []):
            line_net = money(
                money(line["unit_price"]) * int(line["quantity"] or 0)
                - money(line["discount_amount"])
                - money(line["header_discount_amount"])
            )
            vat_multiplier = Decimal("1.00") + (money(line["vat_rate"]) / Decimal("100"))
            weighted_rows.append((line["id"], money(line_net * vat_multiplier)))

        allocations = allocate_customer_total(sale["total_amount"], weighted_rows)
        for line_id, raw_gross in weighted_rows:
            target_gross = allocations.get(line_id, Decimal("0.00"))
            line_customer_gross[line_id] = target_gross
            connection.execute(
                sa.text(
                    "UPDATE sale_items SET rounding_adjustment_amount=:adjustment WHERE id=:line_id"
                ),
                {"adjustment": str(money(target_gross - raw_gross)), "line_id": line_id},
            )

        if money(sum(allocations.values(), Decimal("0.00"))) != money(sale["total_amount"]):
            raise RuntimeError(f"Sipariş satır yuvarlaması mutabık değil: sale={sale['id']}")

    returned_offsets = defaultdict(int)
    return_rows = connection.execute(
        sa.text(
            "SELECT ri.id, ri.product_id, ri.original_sale_item_id, ri.quantity, ri.refund_amount "
            "FROM return_items ri JOIN returns r ON r.id=ri.return_id "
            "ORDER BY r.return_date, ri.id"
        )
    ).mappings().all()
    for row in return_rows:
        product = products.get(row["product_id"])
        line = line_lookup.get(row["original_sale_item_id"])
        refund_amount = money(row["refund_amount"])

        if refund_amount > 0 and line is not None:
            delivered_quantity = int(line["delivered_quantity"] or line["quantity"] or 0)
            quantity = int(row["quantity"] or 0)
            start_index = returned_offsets[line["id"]]
            unit_amounts = allocate_unit_amounts(
                line_customer_gross.get(line["id"], Decimal("0.00")),
                delivered_quantity,
            )
            if start_index + quantity > delivered_quantity:
                raise RuntimeError(f"İade brüt dağıtımı teslim adedini aşıyor: return_item={row['id']}")
            gross_refund = money(sum(unit_amounts[start_index : start_index + quantity], Decimal("0.00")))
            returned_offsets[line["id"]] += quantity
            unit_cost = line["unit_cost_snapshot"]
            product_code = line["product_code_snapshot"]
            product_name = line["product_name_snapshot"]
            product_variant = line["product_variant_snapshot"]
        else:
            if product is None:
                raise RuntimeError(f"İade satırının ürün kaydı bulunamadı: return_item={row['id']}")
            signed_gross = round_customer_price(abs(refund_amount) * VAT_MULTIPLIER)
            gross_refund = money(signed_gross if refund_amount >= 0 else -signed_gross)
            unit_cost = product["purchase_price"]
            product_code = product["product_code"]
            product_name = product["name"]
            product_variant = product["variant"]

        connection.execute(
            sa.text(
                "UPDATE return_items SET gross_refund_amount=:gross_refund, "
                "unit_cost_snapshot=:unit_cost, product_code_snapshot=:product_code, "
                "product_name_snapshot=:product_name, product_variant_snapshot=:product_variant "
                "WHERE id=:return_item_id"
            ),
            {
                "gross_refund": str(gross_refund),
                "unit_cost": str(money(unit_cost)),
                "product_code": product_code,
                "product_name": product_name,
                "product_variant": product_variant,
                "return_item_id": row["id"],
            },
        )

    connection.execute(
        sa.text(
            "UPDATE permissions SET name='Satış sipariş satırlarını görüntüle' "
            "WHERE code='sales.access'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE permissions SET name='Satış siparişini yeniden düzenle' "
            "WHERE code='sales.action.edit'"
        )
    )

    with op.batch_alter_table("return_items") as batch_op:
        batch_op.alter_column(
            "gross_refund_amount", existing_type=sa.Numeric(10, 2), nullable=False
        )
        batch_op.alter_column(
            "unit_cost_snapshot", existing_type=sa.Numeric(10, 2), nullable=False
        )
        batch_op.alter_column(
            "product_code_snapshot", existing_type=sa.String(length=32), nullable=False
        )
        batch_op.alter_column(
            "product_name_snapshot", existing_type=sa.String(length=150), nullable=False
        )


def downgrade():
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE permissions SET name='Satış yönetimini görüntüle' WHERE code='sales.access'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE permissions SET name='Geçmiş satışı yeniden düzenle' "
            "WHERE code='sales.action.edit'"
        )
    )
    with op.batch_alter_table("return_items") as batch_op:
        batch_op.drop_column("product_variant_snapshot")
        batch_op.drop_column("product_name_snapshot")
        batch_op.drop_column("product_code_snapshot")
        batch_op.drop_column("unit_cost_snapshot")
        batch_op.drop_column("gross_refund_amount")
