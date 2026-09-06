import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from flask import session

from app import create_app
from app.extensions import db
from app.models import Package, Product, Sale, SaleItem, Site, Store
from app.modules.sales.routes import (
    VAT_MULTIPLIER,
    VAT_RATE,
    build_sale_receipt_context,
    calculate_sale_breakdown,
    get_sale_edit_discount_amount,
)
from app.services.product_inventory import reserve_barcodes_for_sale, sync_product_barcodes
from config import BaseConfig


class SalesVatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_path = Path(__file__).resolve().parent / f"_sales_vat_{uuid4().hex}.db"
        cls.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.database_path.as_posix()}"
        cls.app = create_app("development")
        cls.app.config["AUTH_ENABLED"] = False
        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = cls.old_database_uri
        cls.database_path.unlink(missing_ok=True)

    def test_vat_constants_are_ten_percent(self):
        self.assertEqual(VAT_RATE, Decimal("0.10"))
        self.assertEqual(VAT_MULTIPLIER, Decimal("1.10"))

    def test_sale_breakdown_uses_ten_percent_vat(self):
        sale = SimpleNamespace(
            total_discount=Decimal("10.00"),
            items=[
                SimpleNamespace(line_total=Decimal("100.00"), discount_amount=Decimal("10.00")),
                SimpleNamespace(line_total=Decimal("50.00"), discount_amount=Decimal("0.00")),
            ],
        )

        breakdown = calculate_sale_breakdown(sale)

        self.assertEqual(breakdown["line_subtotal"], Decimal("150.00"))
        self.assertEqual(breakdown["line_discount_total"], Decimal("10.00"))
        self.assertEqual(breakdown["footer_discount_amount"], Decimal("0.00"))
        self.assertEqual(breakdown["net_subtotal"], Decimal("150.00"))
        self.assertEqual(breakdown["vat_amount"], Decimal("15.00"))
        self.assertEqual(breakdown["gross_total"], Decimal("165.00"))

    def test_receipt_context_builds_gross_lines_with_ten_percent_vat(self):
        sale = SimpleNamespace(
            id=7,
            document_no=7,
            site=SimpleNamespace(code="TEST"),
            sale_date=SimpleNamespace(strftime=lambda fmt: "20260412"),
            created_at=SimpleNamespace(strftime=lambda fmt: "20260412"),
            total_discount=Decimal("0.00"),
            items=[
                SimpleNamespace(
                    quantity=2,
                    line_total=Decimal("100.00"),
                    discount_amount=Decimal("0.00"),
                    product=SimpleNamespace(name="Test Elbise", variant="M"),
                )
            ],
        )

        with self.app.test_request_context("/sales/7/receipt", base_url="http://127.0.0.1:5000/"):
            receipt = build_sale_receipt_context(sale)

        self.assertEqual(receipt["net_subtotal"], Decimal("100.00"))
        self.assertEqual(receipt["vat_amount"], Decimal("10.00"))
        self.assertEqual(receipt["line_items"][0]["gross_total"], Decimal("110.00"))
        self.assertEqual(receipt["line_items"][0]["vat_rate"], 10)

    def test_pos_page_shows_ten_percent_vat_label(self):
        response = self.app.test_client().get("/sales/pos")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("KDV (%10)", html)
        self.assertIn("vatRate: 0.1", html)

    def test_sale_edit_discount_amount_preserves_existing_discount(self):
        sale = SimpleNamespace(
            total_amount=Decimal("200.00"),
            items=[
                SimpleNamespace(unit_price=Decimal("100.00"), quantity=2),
            ],
        )

        self.assertEqual(get_sale_edit_discount_amount(sale), Decimal("20.00"))

    def test_sale_allocation_requires_each_exact_unit_barcode(self):
        with self.app.test_request_context("/"):
            package = Package(code="BARCODE-TEST", name="Barkod Test")
            db.session.add(package)
            db.session.flush()
            site = Site(package_id=package.id, code="BRC", name="Barkod Test")
            db.session.add(site)
            db.session.flush()
            store = Store(site_id=site.id, code="MAIN", name="Ana Mağaza")
            db.session.add(store)
            db.session.flush()
            session["active_site_id"] = site.id
            session["active_store_id"] = store.id

            product = Product(
                site_id=site.id,
                name="Barkodlu Ürün",
                category="Test",
                barcode="990000000001",
                product_code="BRC000001",
                purchase_price=Decimal("100.00"),
                sale_price=Decimal("200.00"),
            )
            db.session.add(product)
            db.session.flush()
            sync_product_barcodes(product, 2)
            db.session.flush()
            exact_barcode = product.product_barcodes[0].barcode
            sale = Sale(
                document_no=1,
                site_id=site.id,
                store_id=store.id,
                payment_method="Nakit",
            )
            sale_item = SaleItem(
                site_id=site.id,
                store_id=store.id,
                sale=sale,
                product=product,
                quantity=1,
                unit_price=Decimal("200.00"),
            )
            db.session.add(sale)

            with self.assertRaisesRegex(ValueError, "tam birim barkodunu"):
                reserve_barcodes_for_sale(product, sale_item, 1, [])
            with self.assertRaisesRegex(ValueError, "bulunamadı"):
                reserve_barcodes_for_sale(
                    product,
                    sale_item,
                    1,
                    [exact_barcode.replace("-", "")],
                )

            allocated = reserve_barcodes_for_sale(product, sale_item, 1, [exact_barcode])
            self.assertEqual([record.barcode for record in allocated], [exact_barcode])
            self.assertEqual(product.stock_quantity, 1)
            db.session.rollback()


if __name__ == "__main__":
    unittest.main()
