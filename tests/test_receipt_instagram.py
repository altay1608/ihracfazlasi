import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from flask import render_template

from app import create_app


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
        self.assertNotIn("İŞLEM SORGULAMA QR", template)
        self.assertNotIn("receipt.qr_url", template)
        self.assertNotIn("receipt.lookup_id", template)
        self.assertIn("Bu belge yalnızca bilgilendirme amaçlıdır", template)
        self.assertIn("mali belge niteliği taşımaz", template)
        self.assertIn('class="thermal-document-type"', template)
        self.assertIn('class="thermal-meta-card"', template)
        self.assertIn('class="thermal-product-row"', template)
        self.assertIn('class="thermal-grand-total"', template)
        self.assertIn("SATILAN ÜRÜNLER", template)

    def test_redesigned_receipt_template_renders_sale_details(self):
        app = create_app("development")
        sale = SimpleNamespace(
            document_no=42,
            sale_date=datetime(2026, 9, 16, 14, 35),
            total_amount=Decimal("2200.00"),
            payment_method="cash",
        )
        receipt = {
            "store": {
                "name": "İhraç Fazlası Giyim",
                "address_line_1": "Merkez Mağaza",
                "address_line_2": "",
                "address_line_3": "",
            },
            "print_time": "14:35",
            "tx_code": "TX-IFG-20260916-042",
            "cashier_name": "Mağaza Yetkilisi",
            "line_items": [
                {
                    "name": "Lacoste T-Shirt (L)",
                    "quantity": 2,
                    "vat_rate": 10,
                    "gross_total": Decimal("2200.00"),
                }
            ],
            "net_subtotal": Decimal("2000.00"),
            "vat_amount": Decimal("200.00"),
        }

        with app.test_request_context("/sales/42/receipt"):
            rendered = render_template(
                "sales/receipt.html",
                sale=sale,
                receipt=receipt,
                payment_methods={"cash": "Nakit"},
                vat_rate=10,
                auto_print=False,
            )

        self.assertIn("Lacoste T-Shirt (L)", rendered)
        self.assertIn("TX-IFG-20260916-042", rendered)
        self.assertIn("GENEL TOPLAM", rendered)


if __name__ == "__main__":
    unittest.main()
