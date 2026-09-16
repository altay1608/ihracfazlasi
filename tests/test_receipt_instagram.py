import unittest
from pathlib import Path


class ReceiptInstagramTests(unittest.TestCase):
    def test_sales_receipt_has_instagram_footer(self):
        template = (
            Path(__file__).resolve().parents[1] / "app/templates/sales/receipt.html"
        ).read_text(encoding="utf-8")

        self.assertIn('class="thermal-instagram"', template)
        self.assertIn("ihrac.fazlasigiyiminegol1", template)
        self.assertIn('class="thermal-instagram-icon"', template)
        self.assertIn('class="thermal-contact"', template)
        self.assertIn("0538 479 36 96", template)


if __name__ == "__main__":
    unittest.main()
