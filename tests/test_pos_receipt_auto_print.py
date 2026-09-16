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


if __name__ == "__main__":
    unittest.main()
