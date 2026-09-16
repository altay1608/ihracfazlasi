import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.finance_reporting import _snapshot_result, build_operating_profit_summary


class OperatingProfitTests(unittest.TestCase):
    def test_daily_result_removes_vat_and_overhead(self):
        product = SimpleNamespace(
            name="Test Tişört",
            variant="M",
            quantity=1,
            net_revenue=Decimal("2000.00"),
            cost=Decimal("1100.00"),
        )
        report = {
            "revenue_after_discount": Decimal("2000.00"),
            "cost": Decimal("1100.00"),
            "products": [product],
        }

        result = build_operating_profit_summary(report, Decimal("200.00"))

        self.assertEqual(result["net_sales"], Decimal("1818.18"))
        self.assertEqual(result["net_cost"], Decimal("1000.00"))
        self.assertEqual(result["gross_profit"], Decimal("818.18"))
        self.assertEqual(result["net_operating_profit"], Decimal("618.18"))
        self.assertEqual(result["product_rows"][0]["allocated_overhead"], Decimal("200.00"))

    def test_daily_overhead_is_distributed_without_rounding_loss(self):
        products = [
            SimpleNamespace(name="A", variant="M", quantity=1, net_revenue=Decimal("550.00"), cost=Decimal("220.00")),
            SimpleNamespace(name="B", variant="L", quantity=1, net_revenue=Decimal("550.00"), cost=Decimal("220.00")),
        ]
        report = {
            "revenue_after_discount": Decimal("1100.00"),
            "cost": Decimal("440.00"),
            "products": products,
        }

        result = build_operating_profit_summary(report, Decimal("200.01"))

        self.assertEqual(
            sum((row["allocated_overhead"] for row in result["product_rows"]), Decimal("0.00")),
            Decimal("200.01"),
        )
        self.assertEqual(result["net_operating_profit"], Decimal("399.99"))

    def test_day_without_sales_starts_at_negative_daily_overhead(self):
        result = build_operating_profit_summary(
            {"revenue_after_discount": 0, "cost": 0, "products": []},
            Decimal("200.00"),
        )

        self.assertEqual(result["net_operating_profit"], Decimal("-200.00"))
        self.assertEqual(result["break_even_remaining"], Decimal("200.00"))
        self.assertEqual(result["product_rows"], [])

    def test_monthly_overhead_uses_real_calendar_day_count(self):
        january = _snapshot_result([], [], Decimal("3100.00"), 0, 0, date(2026, 1, 1), date(2026, 1, 31))
        february = _snapshot_result([], [], Decimal("2800.00"), 0, 0, date(2026, 2, 1), date(2026, 2, 28))

        self.assertEqual(january["planned_daily_overhead"], Decimal("100.00"))
        self.assertEqual(february["planned_daily_overhead"], Decimal("100.00"))


if __name__ == "__main__":
    unittest.main()
