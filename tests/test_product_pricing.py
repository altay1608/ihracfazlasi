import unittest
from decimal import Decimal

from app.services.product_inventory import (
    compute_sale_price,
    compute_sale_price_gross_target,
    get_customer_gross_amount,
    round_customer_price,
)


class ProductPricingTests(unittest.TestCase):
    def test_sale_price_is_stored_without_vat_from_gross_purchase_multiplier(self):
        self.assertEqual(compute_sale_price(Decimal("675.00"), Decimal("3.50")), Decimal("2362.50"))

    def test_gross_table_price_uses_purchase_gross_times_multiplier(self):
        sale_price = compute_sale_price(Decimal("600.00"), Decimal("2.25"))

        self.assertEqual((sale_price * Decimal("1.10")).quantize(Decimal("0.01")), Decimal("1485.00"))

    def test_form_gross_target_uses_purchase_gross_times_multiplier(self):
        self.assertEqual(
            compute_sale_price_gross_target(Decimal("675.00"), Decimal("3.50")),
            Decimal("2598.75"),
        )

    def test_customer_price_rounds_down_below_five_lira_threshold(self):
        self.assertEqual(round_customer_price(Decimal("742.50")), Decimal("740.00"))

    def test_customer_price_rounds_up_after_five_lira_threshold(self):
        self.assertEqual(round_customer_price(Decimal("745.50")), Decimal("750.00"))

    def test_customer_gross_amount_uses_vat_and_customer_rounding(self):
        self.assertEqual(get_customer_gross_amount(Decimal("477.27")), Decimal("525.00"))
        self.assertEqual(get_customer_gross_amount(Decimal("-477.27")), Decimal("-525.00"))


if __name__ == "__main__":
    unittest.main()
