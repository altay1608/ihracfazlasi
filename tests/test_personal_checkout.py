import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import test_finance as fixture
from app.extensions import db
from app.models import Product, Sale, SalePayment, FinanceAccount, FinanceMovement, PosReconciliation, InventoryTransaction
from app.services.finance import activate_finance, get_account_balance, credit_sale_summary
from app.services.product_inventory import sync_product_barcodes
from app.services.reporting import build_profit_product_rows


class PersonalCheckoutTests(unittest.TestCase):
    setUp = fixture.FinanceModuleTests.setUp
    tearDown = fixture.FinanceModuleTests.tearDown

    def prepare(self, mode="shared"):
        activate_finance(self.site.id, self.store.id, activated_at=datetime.utcnow() - timedelta(minutes=1))
        product = Product(name="Şahsi Tişört", category="Tişört", product_code="P1", barcode="P1",
                          sale_price=2000, purchase_price=1000, barcode_mode=mode)
        db.session.add(product)
        db.session.flush()
        sync_product_barcodes(product, 3)
        db.session.commit()
        self.product_id = product.id
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["auth_csrf_token"] = "test-token"
        self.headers = {"X-CSRFToken": "test-token"}
        return product

    def item(self, kind="personal", quantity=1):
        return {"product_id": self.product_id, "quantity": quantity, "unit_price": 2000, "line_type": kind}

    def complete(self, payload):
        with patch("app.modules.sales.routes.Sale", side_effect=lambda **kw: Sale(site_id=self.site.id, store_id=self.store.id, **kw)):
            return self.client.post("/sales/complete", json=payload, headers=self.headers)

    def balances(self):
        return {a.code: get_account_balance(a) for a in FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id)}

    def test_personal_checkout_without_payment_preserves_money_and_cost(self):
        self.prepare()
        balances = self.balances()
        response = self.complete({"items": [self.item()]})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        sale = Sale.query.one()
        self.assertEqual(sale.total_amount, 0)
        self.assertEqual(sale.payment_method, "Ödeme Alınmadı")
        self.assertEqual(sale.payment_status_label, "Ödeme Alınmadı")
        self.assertEqual(SalePayment.query.count(), 0)
        self.assertEqual(credit_sale_summary(sale)["remaining"], 0)
        self.assertIsNone(sale.payment_due_date)
        self.assertEqual(db.session.get(Product, self.product_id).stock_quantity, 2)
        self.assertEqual(self.balances(), balances)
        self.assertEqual(FinanceMovement.query.filter_by(source_type="sale").count(), 0)
        self.assertEqual(PosReconciliation.query.count(), 0)
        movement = InventoryTransaction.query.filter_by(transaction_code="PERSONAL-OUT").one()
        self.assertEqual(movement.quantity_delta, -1)
        self.assertEqual(movement.total_cost, Decimal("1000"))
        self.assertEqual(sale.items[0].unit_cost_snapshot, Decimal("1000"))
        self.assertEqual(build_profit_product_rows([sale]), [])
        receipt = self.client.get(response.json["receipt_url"])
        self.assertEqual(receipt.status_code, 200)
        self.assertIn("ÖDEME ALINMADI", receipt.get_data(as_text=True))
        self.assertIn("ŞAHSİ KULLANIM", receipt.get_data(as_text=True))
        detail = self.client.get(f"/sales/{sale.id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("İşletme Sahibinin Aldığı Ürünler", detail.get_data(as_text=True))

    def test_stale_split_credit_is_ignored_for_non_sale_cart(self):
        self.prepare()
        response = self.complete({"payment_method": "__split__", "payments": [{"payment_method": "Veresiye", "amount": 2200}], "items": [self.item()]})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertFalse(Sale.query.one().payments)
        self.assertEqual(PosReconciliation.query.count(), 0)

    def test_mixed_cart_only_posts_paid_item_and_keeps_one_receipt(self):
        self.prepare()
        response = self.complete({"payment_method": "__split__", "payments": [
            {"payment_method": "Nakit", "amount": 1500},
            {"payment_method": "Veresiye", "amount": 700, "due_date": "2026-12-01"}],
            "customer": {"customer_name": "Test"}, "items": [self.item(), self.item("sale")]})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        sale = Sale.query.one()
        self.assertEqual(sale.total_amount, 2200)
        self.assertEqual(credit_sale_summary(sale)["remaining"], 700)
        self.assertEqual(self.balances()["CASH"], 1500)
        self.assertEqual(self.balances()["CREDIT"], 700)
        self.assertEqual(db.session.get(Product, self.product_id).stock_quantity, 1)
        self.assertEqual(len(sale.items), 2)
        rows = build_profit_product_rows([sale])
        self.assertEqual(sum(row.quantity for row in rows), 1)
        self.assertEqual(sum(row.profit for row in rows), 1100)

    def test_payment_flag_cannot_bypass_paid_sale(self):
        self.prepare()
        response = self.complete({"payment_method": "Ödeme Alınmadı", "items": [self.item("sale")]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Sale.query.count(), 0)
        self.assertEqual(db.session.get(Product, self.product_id).stock_quantity, 3)

    def test_insufficient_stock_rolls_back_non_sale_cart(self):
        self.prepare()
        response = self.complete({"items": [self.item(quantity=2), self.item(quantity=2)]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Sale.query.count(), 0)
        self.assertEqual(db.session.get(Product, self.product_id).stock_quantity, 3)

    def test_unit_barcode_reserved_for_personal_use(self):
        product = self.prepare("unit")
        item = self.item()
        item["scanned_barcodes"] = [product.product_barcodes[0].barcode]
        response = self.complete({"items": [item]})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        sale = Sale.query.one()
        self.assertEqual(len(sale.items[0].product_barcodes), 1)
        self.assertEqual(sale.items[0].product_barcodes[0].status, "sold")
        self.assertEqual(product.stock_quantity, 2)

    def test_edit_sale_to_personal_reverses_money_without_double_stock_drop(self):
        self.prepare()
        response = self.complete({"payment_method": "Nakit", "items": [self.item("sale")]})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        sale_id = response.json["sale_id"]
        self.assertEqual(self.balances()["CASH"], 2200)
        response = self.client.post(f"/sales/{sale_id}/update", json={"items": [self.item()]}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(self.balances()["CASH"], 0)
        self.assertEqual(db.session.get(Product, self.product_id).stock_quantity, 2)
        self.assertEqual(SalePayment.query.count(), 0)
        response = self.client.post(f"/sales/{sale_id}/update", json={"payment_method": "Nakit", "items": [self.item("sale")]}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(self.balances()["CASH"], 2200)
        self.assertEqual(db.session.get(Product, self.product_id).stock_quantity, 2)

    def test_gift_still_has_cost_but_no_payment(self):
        self.prepare()
        response = self.complete({"items": [self.item("gift")]})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        rows = build_profit_product_rows([Sale.query.one()])
        self.assertEqual(rows[0].profit, -1100)
        self.assertEqual(self.balances()["CASH"], 0)
