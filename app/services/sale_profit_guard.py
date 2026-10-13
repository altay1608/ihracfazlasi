"""Advisory 110% cost markup check; does not change prices or accounting."""
from decimal import Decimal, ROUND_FLOOR
from app.utils import quantize_amount


class ProfitConfirmationRequired(ValueError):
    def __init__(self, warnings):
        super().__init__("Bazı ürünler %110 kâr + KDV sınırının altında. Yine de tamamlamak istiyor musunuz?")
        self.warnings = warnings


def profit_warnings(items, final_total, vat_multiplier):
    lines = [item for item in items if (item.line_type or "sale") == "sale"]
    if not lines:
        return []
    bases = [max(quantize_amount(item.unit_price * item.quantity - (item.discount_amount or 0)), Decimal("0")) for item in lines]
    base = sum(bases, Decimal("0"))
    cents = int(quantize_amount(final_total) * 100)
    # Largest-remainder allocation keeps the sum equal to the exact charged total.
    raw = [Decimal(cents) * value / base if base else Decimal("0") for value in bases]
    allocated = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in raw]
    if base:
        order = sorted(range(len(lines)), key=lambda i: raw[i] - allocated[i], reverse=True)
        for i in order[:cents - sum(allocated)]:
            allocated[i] += 1
    warnings = []
    for item, amount in zip(lines, allocated):
        minimum = quantize_amount(Decimal(item.product.purchase_price or 0) * Decimal("2.10") * vat_multiplier * item.quantity)
        charged = Decimal(amount) / 100
        if charged < minimum:
            warnings.append({"product_id": item.product.id, "name": item.product.name,
                "variant": item.product.variant or "", "quantity": item.quantity,
                "charged_total": str(charged), "minimum_total": str(minimum)})
    return warnings


def require_profit_confirmation(sale, payload, vat_multiplier):
    warnings = profit_warnings(sale.items, sale.total_amount, vat_multiplier)
    if warnings and payload.get("profit_warning_confirmed") is not True:
        raise ProfitConfirmationRequired(warnings)
