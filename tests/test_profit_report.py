import unittest
from decimal import Decimal
from types import SimpleNamespace

from app.services.reporting import build_daily_distribution_rows, build_profit_product_rows, sum_return_items_customer_gross


class ProfitReportTests(unittest.TestCase):
    def test_product_rows_show_cost_markup_and_sales_margin_with_vat(self):
        product = SimpleNamespace(id=1, name="Test Ürün", variant="M", purchase_price=Decimal("600.00"))
        sale = SimpleNamespace(
            total_amount=Decimal("1485.00"),
            total_discount=Decimal("0.00"),
            items=[
                SimpleNamespace(
                    product=product,
                    quantity=1,
                    unit_price=Decimal("1350.00"),
                    discount_amount=Decimal("0.00"),
                )
            ],
        )

        row = build_profit_product_rows([sale])[0]

        self.assertEqual(row.net_revenue, Decimal("1485.00"))
        self.assertEqual(row.cost, Decimal("660.00"))
        self.assertEqual(row.profit, Decimal("825.00"))
        self.assertEqual(row.cost_profit_rate, Decimal("125.00"))
        self.assertEqual(row.sales_margin_rate, Decimal("55.56"))

    def test_return_refunds_are_reported_as_customer_gross_amounts(self):
        return_items = [
            SimpleNamespace(refund_amount=Decimal("477.27")),
            SimpleNamespace(refund_amount=Decimal("-100.00")),
        ]

        self.assertEqual(sum_return_items_customer_gross(return_items), Decimal("415.00"))

    def test_profit_rows_cancel_sale_when_item_is_returned_in_same_range(self):
        product = SimpleNamespace(id=1, name="Test Urun", variant="M", purchase_price=Decimal("150.00"))
        sale = SimpleNamespace(
            total_amount=Decimal("525.00"),
            total_discount=Decimal("0.00"),
            items=[
                SimpleNamespace(
                    product=product,
                    quantity=1,
                    unit_price=Decimal("477.27"),
                    discount_amount=Decimal("0.00"),
                )
            ],
        )
        return_item = SimpleNamespace(
            product=product,
            quantity=1,
            refund_amount=Decimal("477.27"),
        )

        self.assertEqual(build_profit_product_rows([sale], [return_item]), [])

    def test_profit_rows_cancel_discounted_sale_when_item_is_returned_in_same_range(self):
        product = SimpleNamespace(id=1, name="Test Urun", variant="M", purchase_price=Decimal("750.00"))
        sale = SimpleNamespace(
            total_amount=Decimal("1850.00"),
            total_discount=Decimal("5.68"),
            items=[
                SimpleNamespace(
                    product=product,
                    quantity=1,
                    unit_price=Decimal("1687.50"),
                    discount_amount=Decimal("0.00"),
                )
            ],
        )
        return_item = SimpleNamespace(
            product=product,
            quantity=1,
            refund_amount=Decimal("1681.82"),
        )

        self.assertEqual(build_profit_product_rows([sale], [return_item]), [])

    def test_profit_rows_ignore_standalone_refund_without_selected_sale(self):
        product = SimpleNamespace(id=1, name="Test Urun", variant="M", purchase_price=Decimal("150.00"))
        return_item = SimpleNamespace(
            product=product,
            quantity=1,
            refund_amount=Decimal("477.27"),
        )

        self.assertEqual(build_profit_product_rows([], [return_item]), [])

    def test_daily_distribution_cancels_sale_when_item_is_returned_in_same_range(self):
        product = SimpleNamespace(id=1, name="Test Urun", variant="M")
        sale_item = SimpleNamespace(
            product=product,
            quantity=1,
            line_total=Decimal("477.27"),
        )
        sale = SimpleNamespace(items=[sale_item])
        return_item = SimpleNamespace(
            product=product,
            quantity=1,
            refund_amount=Decimal("477.27"),
        )

        self.assertEqual(build_daily_distribution_rows([sale], [return_item]), [])

    def test_daily_distribution_cancels_discounted_sale_when_item_is_returned_in_same_range(self):
        product = SimpleNamespace(id=1, name="Test Urun", variant="M")
        sale_item = SimpleNamespace(
            product=product,
            quantity=1,
            line_total=Decimal("1687.50"),
        )
        sale = SimpleNamespace(items=[sale_item])
        return_item = SimpleNamespace(
            product=product,
            quantity=1,
            refund_amount=Decimal("1681.82"),
        )

        self.assertEqual(build_daily_distribution_rows([sale], [return_item]), [])

    def test_daily_distribution_ignores_standalone_refund_without_selected_sale(self):
        product = SimpleNamespace(id=1, name="Test Urun", variant="M")
        return_item = SimpleNamespace(
            product=product,
            quantity=1,
            refund_amount=Decimal("477.27"),
        )

        self.assertEqual(build_daily_distribution_rows([], [return_item]), [])

    def test_daily_distribution_applies_footer_discount_and_matches_collected_total(self):
        product = SimpleNamespace(id=1, name="Test Urun", variant="M")
        sale_item = SimpleNamespace(
            product=product,
            quantity=1,
            unit_price=Decimal("742.50"),
            discount_amount=Decimal("0.00"),
            line_total=Decimal("742.50"),
        )
        sale = SimpleNamespace(
            total_amount=Decimal("800.00"),
            total_discount=Decimal("15.23"),
            items=[sale_item],
        )

        row = build_daily_distribution_rows([sale])[0]

        self.assertEqual(row.quantity, 1)
        self.assertEqual(row.revenue, Decimal("727.27"))
        self.assertEqual(row.revenue_gross, Decimal("800.00"))

    def test_daily_distribution_preserves_multi_line_collected_total(self):
        products = [
            SimpleNamespace(id=index, name=f"Test Urun {index}", variant="STD")
            for index in range(1, 4)
        ]
        items = [
            SimpleNamespace(
                product=product,
                quantity=1,
                unit_price=Decimal("303.03"),
                discount_amount=Decimal("0.00"),
                line_total=Decimal("303.03"),
            )
            for product in products
        ]
        sale = SimpleNamespace(
            total_amount=Decimal("1000.00"),
            total_discount=Decimal("0.00"),
            items=items,
        )

        rows = build_daily_distribution_rows([sale])

        self.assertEqual(sum((row.revenue_gross for row in rows), Decimal("0.00")), Decimal("1000.00"))


if __name__ == "__main__":
    unittest.main()
