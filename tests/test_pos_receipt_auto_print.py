import unittest
from pathlib import Path


class PosReceiptAutoPrintTests(unittest.TestCase):
    def test_completed_sale_returns_receipt_url(self):
        source = (Path(__file__).resolve().parents[1] / "app/modules/sales/routes.py").read_text(encoding="utf-8")

        self.assertIn('"receipt_url": url_for("sales.receipt", sale_id=sale.id)', source)

    def test_pos_preopens_receipt_window_and_navigates_after_success(self):
        source = (Path(__file__).resolve().parents[1] / "app/static/js/pos.js").read_text(encoding="utf-8")

        self.assertIn('window.open("about:blank", "_blank")', source)
        self.assertIn("receiptWindow.location.replace(data.receipt_url)", source)
        self.assertIn("receiptWindow.close()", source)
        self.assertNotIn("receiptWindow.opener = null", source)

    def test_pos_supports_gift_and_personal_line_types(self):
        source = (Path(__file__).resolve().parents[1] / "app/static/js/pos.js").read_text(encoding="utf-8")

        self.assertIn('<option value="gift"', source)
        self.assertIn('<option value="personal"', source)
        self.assertIn('line_type: item.line_type || "sale"', source)
        self.assertIn('(item.line_type || "sale") === "sale"', source)

    def test_pos_supports_split_payments_and_exact_total_validation(self):
        javascript = (Path(__file__).resolve().parents[1] / "app/static/js/pos.js").read_text(encoding="utf-8")
        template = (Path(__file__).resolve().parents[1] / "app/templates/sales/pos.html").read_text(encoding="utf-8")

        self.assertIn('value="__split__"', template)
        self.assertIn('data-split-payment="{{ method }}"', template)
        self.assertIn("collectSplitPayments", javascript)
        self.assertIn("Parçalı ödeme toplamı satış tutarına eşit olmalıdır.", javascript)
        self.assertIn("payments: splitSummary?.payments || null", javascript)


if __name__ == "__main__":
    unittest.main()
