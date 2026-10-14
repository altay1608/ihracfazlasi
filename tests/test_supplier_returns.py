import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch
import test_finance as fixture
from app.extensions import db
from app.models import Product, ProductBarcode, SupplierReturn, FinanceAccount, FinanceCategory, CurrentEntry, RetailMultiplier
from app.services.finance import activate_finance, create_current_account, create_current_entry, get_account_balance, reverse_movement
from app.services.finance_operations import create_expense
from app.services.finance_reporting import actual_expenses_between
from app.services.supplier_returns import create_supplier_return
from app.services.product_inventory import sync_product_barcodes, compute_sale_price
from app.utils import now_in_istanbul


class SupplierReturnTests(unittest.TestCase):
    setUp = fixture.FinanceModuleTests.setUp
    tearDown = fixture.FinanceModuleTests.tearDown

    def setup_records(self, mode="unit"):
        activate_finance(self.site.id, self.store.id, opening_cash=1000, activated_at=datetime.utcnow()-timedelta(days=1))
        supplier = create_current_account(site_id=self.site.id, account_category="supplier", name="Test Toptancı")
        debt = create_current_entry(site_id=self.site.id, store_id=self.store.id, current_account_id=supplier.id,
            entry_type="payable", amount=5000)
        product = Product(site_id=self.site.id, name="Test Pantolon", category="Pantolon", variant="32",
            product_code="P-1", barcode="P-1", purchase_price=100, sale_price=300, barcode_mode=mode)
        db.session.add(product)
        db.session.flush()
        sync_product_barcodes(product, 3)
        db.session.commit()
        self.product, self.debt, self.supplier = product, debt, supplier
        self.cash = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code="CASH").one()
        return dict(site_id=self.site.id, store_id=self.store.id, supplier_id=supplier.id, product_id=product.id,
            quantity=1, amount=100, mode="debt", reason="Kusurlu ürün iadesi", request_key=str(uuid4()),
            current_entry_id=debt.id, barcodes=[product.product_barcodes[0].barcode])

    def test_debt_return_is_atomic_idempotent_and_preserves_cash(self):
        args = self.setup_records()
        row = create_supplier_return(**args)
        db.session.commit()
        create_supplier_return(**args)
        db.session.commit()
        self.assertEqual(self.debt.remaining_amount, 4900)
        self.assertEqual(self.product.stock_quantity, 2)
        self.assertEqual(get_account_balance(self.cash), 1000)
        self.assertEqual(SupplierReturn.query.count(), 1)
        self.assertEqual(ProductBarcode.query.filter_by(barcode=args["barcodes"][0]).one().status, "supplier_returned")
        client = self.app.test_client()
        response = client.get("/finance/operations/supplier-returns")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test Toptancı", response.get_data(as_text=True))
        response = client.get("/finance/current-accounts")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Ürün İadesiyle Düşülen", response.get_data(as_text=True))

    def test_shared_refund_changes_cash_not_debt_or_profit(self):
        args = self.setup_records("shared")
        args.update(mode="refund", account_id=self.cash.id, quantity=2, amount=200, barcodes=[])
        create_supplier_return(**args)
        db.session.commit()
        self.assertEqual(self.debt.remaining_amount, 5000)
        self.assertEqual(self.product.stock_quantity, 1)
        self.assertEqual(get_account_balance(self.cash), 1200)
        today = now_in_istanbul().date()
        self.assertEqual(actual_expenses_between(self.site.id, self.store.id, today, today)["total"], 0)

    def test_reject_invalid_barcode_amount_and_scope(self):
        args = self.setup_records()
        for changes in ({"barcodes": ["wrong"]}, {"amount": 6000}, {"store_id": 999}, {"quantity": 4}):
            with self.assertRaises(ValueError):
                create_supplier_return(**{**args, **changes})
            db.session.rollback()
            self.assertEqual(self.product.stock_quantity, 3)
            self.assertEqual(self.debt.remaining_amount, 5000)
        client = self.app.test_client()
        self.assertEqual(client.post("/finance/operations/supplier-returns", data={}).status_code, 400)
        with patch("app.services.access_control.has_permission", return_value=False):
            self.assertEqual(client.get("/finance/operations/supplier-returns").status_code, 403)

    def test_actual_expense_is_dated_and_reversal_aware(self):
        self.setup_records()
        today = now_in_istanbul().date()
        category = FinanceCategory.query.filter_by(site_id=self.site.id, code="MANUAL_OUT").one()
        expense = create_expense(site_id=self.site.id, store_id=self.store.id, account_id=self.cash.id,
            category_id=category.id, expense_date=today, vendor="Kargo", document_no="F1",
            description="Kargo ödemesi", net_amount=100, vat_amount=20, config={})
        db.session.flush()
        self.assertEqual(actual_expenses_between(self.site.id, self.store.id, today, today)["total"], 120)
        self.assertEqual(actual_expenses_between(self.site.id, 999, today, today)["total"], 0)
        from app.models import FinanceMovement
        reverse_movement(db.session.get(FinanceMovement, expense.movement_id), "Yanlış kayıt")
        db.session.flush()
        self.assertEqual(actual_expenses_between(self.site.id, self.store.id, today, today)["total"], 0)
        self.assertEqual(self.app.test_client().get("/finance/operations/").status_code, 200)

    def test_bulk_price_preview_requires_confirmation(self):
        self.setup_records()
        multiplier = RetailMultiplier(name="Test", multiplier=Decimal("3.25"))
        db.session.add(multiplier)
        db.session.commit()
        client = self.app.test_client()
        with client.session_transaction() as session:
            session["auth_csrf_token"] = "test"
        data = {"product_ids": str(self.product.id), "retail_multiplier_id": str(multiplier.id)}
        response = client.get("/products/bulk/multiplier", query_string={"product_ids": self.product.id})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Eski fiyat", response.get_data(as_text=True))
        response = client.post("/products/bulk/multiplier", data=data, headers={"X-CSRF-Token": "test"})
        self.assertEqual(response.status_code, 400)
        data["preview_confirmed"] = str(multiplier.id)
        response = client.post("/products/bulk/multiplier", data=data, headers={"X-CSRF-Token": "test"})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(self.product.sale_price, compute_sale_price(100, Decimal("3.25")))
        self.assertEqual(self.product.stock_quantity, 3)
