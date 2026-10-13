from datetime import date, datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

import test_lobby_finance as fixture
from app.extensions import db
from app.models import Product, Sale, SaleItem, SalePayment
from app.modules.sales.routes import apply_sale_payload, build_sale_receipt_context
from app.services.customer_orders import prepare_customer_order


class CustomerCreditTests(unittest.TestCase):
    setUp = fixture.LobbyFinanceTests.setUp
    tearDown = fixture.LobbyFinanceTests.tearDown

    def product(self):
        product = Product(name="Test Tişört", category="Tişört", product_code="12345",
                          barcode="12345", sale_price=Decimal("1625"), purchase_price=100,
                          stock_quantity=10, barcode_mode="shared")
        db.session.add(product)
        db.session.flush()
        return product

    def test_cent_exact_vat_and_discount_receipt(self):
        product = self.product()
        with self.app.test_request_context("/sales/complete"), patch(
            "app.modules.sales.routes.reserve_barcodes_for_sale"
        ):
            sale = Sale(payment_method="Nakit", sale_date=datetime(2026, 10, 13), document_no=1)
            payload = {"payment_method": "Nakit", "items": [{"product_id": product.id, "quantity": 1, "unit_price": "1625"}]}
            apply_sale_payload(sale, payload)
            self.assertEqual(sale.total_amount, Decimal("1787.50"))
            prepare_customer_order(sale)
            receipt = build_sale_receipt_context(sale)
            self.assertEqual(receipt["vat_amount"], Decimal("162.50"))
            self.assertEqual(receipt["discount_gross"], 0)
            discounted = Sale(payment_method="Nakit", sale_date=datetime(2026, 10, 13), document_no=2)
            payload["target_final_total"] = "1700"
            apply_sale_payload(discounted, payload)
            prepare_customer_order(discounted)
            receipt = build_sale_receipt_context(discounted)
            self.assertEqual(discounted.total_amount, Decimal("1700.00"))
            self.assertEqual(receipt["discount_gross"], Decimal("87.50"))

    def test_split_credit_stays_open_and_legacy_paid_is_visible(self):
        product = self.product()
        sale = Sale(site_id=1, store_id=1, document_no=1, payment_method="Parçalı Ödeme", total_amount=110, total_discount=0,
                    customer_name="Veresiye Test Müşterisi", payment_due_date=date(2026, 12, 1))
        sale.items.append(SaleItem(product=product, quantity=1, unit_price=100, discount_amount=0))
        sale.payments.extend([
            SalePayment(payment_method="Nakit", amount=50, status="PAID"),
            SalePayment(payment_method="Veresiye", amount=60, status="OPEN", due_date=date(2026, 12, 1)),
        ])
        prepare_customer_order(sale)
        self.assertEqual(sale.payment_status, "OPEN")
        sale.payment_status = "PAID"  # legacy record affected by the previous bug
        sale.payment_due_date = None  # legacy missing date must not hide the debt
        db.session.add(sale)
        db.session.commit()
        response = self.app.test_client().get("/finance/operations/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Veresiye Test Müşterisi", html)
        self.assertIn("Vade belirtilmemiş", html)
        self.assertIn("Ödeme Al", html)

    def test_customer_search_finds_old_receipt(self):
        product = self.product()
        sale = Sale(site_id=1, store_id=1, document_no=1, customer_name="Eski Müşteri", customer_mobile="05380000000",
                    sale_date=datetime(2025, 1, 1), payment_method="Nakit", total_amount=110)
        sale.items.append(SaleItem(product=product, quantity=1, unit_price=100, discount_amount=0))
        prepare_customer_order(sale)
        db.session.add(sale)
        db.session.commit()
        client = self.app.test_client()
        response = client.get("/sales/", query_string={"customer": "Eski Müşteri"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"/sales/{sale.id}/receipt", response.get_data(as_text=True))
        self.assertIn("Tüm tarihler", response.get_data(as_text=True))
        response = client.get("/sales/", query_string={"customer": "Bulunmayan"})
        self.assertNotIn(f"/sales/{sale.id}/receipt", response.get_data(as_text=True))
