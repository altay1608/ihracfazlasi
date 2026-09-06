from __future__ import annotations

from decimal import Decimal

from app.services.product_inventory import round_customer_price
from app.utils import quantize_amount


VAT_RATE = Decimal("0.10")
VAT_MULTIPLIER = Decimal("1.10")

ORDER_STATUS_DELIVERED = "DELIVERED"
ORDER_STATUS_PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
ORDER_STATUS_RETURNED = "RETURNED"

PAYMENT_STATUS_PAID = "PAID"
PAYMENT_STATUS_PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
PAYMENT_STATUS_REFUNDED = "REFUNDED"

LINE_STATUS_DELIVERED = "DELIVERED"
LINE_STATUS_PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
LINE_STATUS_RETURNED = "RETURNED"
LINE_STATUS_CANCELLED = "CANCELLED"


def _active_lines(order):
    return [line for line in order.items if line.line_status != LINE_STATUS_CANCELLED]


def _allocate_amount(total, weighted_lines):
    total = quantize_amount(total)
    weights = [max(quantize_amount(weight), Decimal("0.00")) for _, weight in weighted_lines]
    weight_total = sum(weights, Decimal("0.00"))
    allocations = {}
    remaining = total

    for index, ((line, _), weight) in enumerate(zip(weighted_lines, weights)):
        if index == len(weighted_lines) - 1:
            allocation = remaining
        elif weight_total:
            allocation = min(quantize_amount((weight / weight_total) * total), remaining)
        else:
            allocation = Decimal("0.00")
        allocations[line] = allocation
        remaining = quantize_amount(remaining - allocation)

    return allocations


def allocate_customer_gross_total(total, weighted_lines):
    """Distribute a rounded customer total without breaking header reconciliation."""
    total = max(quantize_amount(total), Decimal("0.00"))
    weights = [max(quantize_amount(weight), Decimal("0.00")) for _, weight in weighted_lines]
    weight_total = sum(weights, Decimal("0.00"))
    allocations = {}
    remaining_total = total
    remaining_weight = weight_total

    for index, ((line, _), weight) in enumerate(zip(weighted_lines, weights)):
        if index == len(weighted_lines) - 1:
            allocation = remaining_total
        elif remaining_weight:
            proportional_amount = quantize_amount((weight / remaining_weight) * remaining_total)
            allocation = min(round_customer_price(proportional_amount), remaining_total)
        else:
            allocation = Decimal("0.00")
        allocations[line] = quantize_amount(allocation)
        remaining_total = quantize_amount(remaining_total - allocation)
        remaining_weight = quantize_amount(remaining_weight - weight)

    return allocations


def allocate_unit_amounts(total, quantity):
    """Split a stored customer total into cent-exact unit shares."""
    quantity = int(quantity or 0)
    if quantity <= 0:
        return []

    total_cents = int(quantize_amount(total) * 100)
    sign = -1 if total_cents < 0 else 1
    base_cents, remainder = divmod(abs(total_cents), quantity)
    return [
        Decimal(sign * (base_cents + (1 if index < remainder else 0))) / Decimal("100")
        for index in range(quantity)
    ]


def calculate_order_line_return_gross(order_line, quantity, already_returned=None):
    delivered_quantity = int(order_line.delivered_quantity or order_line.quantity or 0)
    already_returned = int(
        order_line.returned_quantity if already_returned is None else already_returned
    )
    quantity = int(quantity or 0)
    if quantity <= 0 or already_returned < 0 or already_returned + quantity > delivered_quantity:
        raise ValueError("İade adedi satış sipariş satırındaki teslim edilen adedi aşamaz.")

    unit_amounts = allocate_unit_amounts(order_line.gross_amount, delivered_quantity)
    return quantize_amount(sum(unit_amounts[already_returned : already_returned + quantity], Decimal("0.00")))


def prepare_customer_order(order):
    """Freeze line context and reconcile line financials with the order header."""
    lines = _active_lines(order)
    for line_no, line in enumerate(lines, start=1):
        product = line.product
        line.line_no = line_no
        line.release_no = line.release_no or 1
        line.line_status = LINE_STATUS_DELIVERED
        line.delivered_quantity = int(line.quantity or 0)
        line.returned_quantity = 0
        line.cancelled_quantity = 0
        line.product_code_snapshot = product.product_code
        line.product_name_snapshot = product.name
        line.product_variant_snapshot = product.variant
        line.product_category_snapshot = product.category
        line.unit_cost_snapshot = quantize_amount(product.purchase_price or 0)
        line.vat_rate = VAT_RATE * 100

    line_discount_total = sum(
        (quantize_amount(line.discount_amount or 0) for line in lines),
        Decimal("0.00"),
    )
    header_discount = max(
        quantize_amount(order.total_discount or 0) - line_discount_total,
        Decimal("0.00"),
    )
    weighted_lines = [
        (
            line,
            quantize_amount((line.unit_price * line.quantity) - (line.discount_amount or 0)),
        )
        for line in lines
    ]
    allocations = _allocate_amount(header_discount, weighted_lines)

    gross_weighted_lines = []
    for line, base_after_line_discount in weighted_lines:
        line.header_discount_amount = allocations.get(line, Decimal("0.00"))
        line.rounding_adjustment_amount = Decimal("0.00")
        line_net = quantize_amount(base_after_line_discount - line.header_discount_amount)
        gross_weighted_lines.append((line, quantize_amount(line_net * VAT_MULTIPLIER)))

    gross_allocations = allocate_customer_gross_total(order.total_amount or 0, gross_weighted_lines)
    for line, raw_gross in gross_weighted_lines:
        line.rounding_adjustment_amount = quantize_amount(
            gross_allocations.get(line, Decimal("0.00")) - raw_gross
        )

    order.order_status = ORDER_STATUS_DELIVERED
    order.payment_status = PAYMENT_STATUS_PAID
    order.currency_code = order.currency_code or "TRY"
    return order


def register_returned_quantity(order_line, quantity):
    quantity = int(quantity or 0)
    next_quantity = int(order_line.returned_quantity or 0) + quantity
    delivered_quantity = int(order_line.delivered_quantity or order_line.quantity or 0)
    if quantity <= 0 or next_quantity > delivered_quantity:
        raise ValueError("İade adedi satış sipariş satırındaki teslim edilen adedi aşamaz.")

    order_line.returned_quantity = next_quantity
    if next_quantity == delivered_quantity:
        order_line.line_status = LINE_STATUS_RETURNED
    else:
        order_line.line_status = LINE_STATUS_PARTIALLY_RETURNED


def refresh_customer_order_return_status(order):
    lines = _active_lines(order)
    delivered_total = sum((int(line.delivered_quantity or 0) for line in lines), 0)
    returned_total = sum((int(line.returned_quantity or 0) for line in lines), 0)

    if returned_total <= 0:
        order.order_status = ORDER_STATUS_DELIVERED
        order.payment_status = PAYMENT_STATUS_PAID
    elif returned_total >= delivered_total:
        order.order_status = ORDER_STATUS_RETURNED
        order.payment_status = PAYMENT_STATUS_REFUNDED
    else:
        order.order_status = ORDER_STATUS_PARTIALLY_RETURNED
        order.payment_status = PAYMENT_STATUS_PARTIALLY_REFUNDED
    return order
