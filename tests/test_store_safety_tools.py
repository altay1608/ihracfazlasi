import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import test_finance as fixture
from app.extensions import db
from app.models import Sale, Product, StoreInventory, FinanceAccount, FinanceMovement
from app.services.finance import (activate_finance, create_account_transfer, get_account_balance,
    sync_sale_finance, collect_credit_sale_payment, credit_sale_remaining)
from app.services.finance_corrections import cancel_finance_document
from app.services.finance_operations import closing_expectations, create_daily_closing, create_expense
from app.models import FinanceCategory
from app.models.finance import PosReconciliation
from app.services.store_tools import due_agenda, slow_stock, customer_history
from scripts.backup_database import backup_database


class StoreSafetyTests(unittest.TestCase):
    setUp = fixture.FinanceModuleTests.setUp
    tearDown = fixture.FinanceModuleTests.tearDown

    def activate(self):
        activate_finance(self.site.id, self.store.id, opening_cash=1000,
                         activated_at=datetime.utcnow() - timedelta(days=1))
        db.session.flush()
        return {row.code: row for row in FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id).all()}

    def test_transfer_correction_is_idempotent_and_scoped(self):
        accounts = self.activate()
        transfer = create_account_transfer(site_id=self.site.id, store_id=self.store.id,
            from_account_id=accounts["CASH"].id, to_account_id=accounts["BANK"].id,
            amount=200, occurred_at=datetime.utcnow())
        cancel_finance_document(self.site.id, self.store.id, "transfer", transfer.id, "Yanlış hesap seçimi")
        cancel_finance_document(self.site.id, self.store.id, "transfer", transfer.id, "Tekrar gönderim")
        self.assertEqual(get_account_balance(accounts["CASH"]), 1000)
        self.assertEqual(get_account_balance(accounts["BANK"]), 0)
        self.assertEqual(FinanceMovement.query.filter(FinanceMovement.reversal_of_id.isnot(None)).count(), 2)
        with self.assertRaises(ValueError):
            cancel_finance_document(self.site.id, 999, "transfer", transfer.id, "Başka mağaza denemesi")

    def test_credit_correction_reopens_debt_without_duplicate_revenue(self):
        accounts = self.activate()
        sale = Sale(site_id=self.site.id, store_id=self.store.id, document_no=1,
            payment_method="Veresiye", total_amount=500, payment_status="OPEN",
            customer_name="Test Müşteri", payment_due_date=date.today(), sale_date=datetime.utcnow())
        db.session.add(sale)
        db.session.flush()
        sync_sale_finance(sale)
        collection = collect_credit_sale_payment(site_id=self.site.id, store_id=self.store.id,
            sale_id=sale.id, payment_method="Nakit", amount=200, occurred_at=datetime.utcnow())
        self.assertEqual(credit_sale_remaining(sale), 300)
        cancel_finance_document(self.site.id, self.store.id, "collection", collection.id, "Yanlış tahsilat kaydı")
        cancel_finance_document(self.site.id, self.store.id, "collection", collection.id, "Tekrar gönderim")
        self.assertEqual(credit_sale_remaining(sale), 500)
        self.assertEqual(get_account_balance(accounts["CASH"]), 1000)
        self.assertEqual(sale.payment_status, "OPEN")

    def test_historical_closing_excludes_future_cash(self):
        accounts = self.activate()
        past = date.today() - timedelta(days=5)
        self.assertEqual(closing_expectations(self.site.id, self.store.id, past)["cash"], 0)
        self.assertEqual(closing_expectations(self.site.id, self.store.id, date.today())["cash"], 1000)

    def test_expense_reversal_preserves_document_and_restores_cash(self):
        accounts = self.activate()
        category = FinanceCategory.query.filter_by(site_id=self.site.id, code="MANUAL_OUT").one()
        expense = create_expense(site_id=self.site.id, store_id=self.store.id,
            account_id=accounts["CASH"].id, category_id=category.id, expense_date=date.today(),
            vendor="Test", document_no="TEST-1", description="Test gideri", net_amount=100,
            vat_amount=20, config={"FINANCE_APPROVAL_LIMIT": "5000"})
        self.assertEqual(get_account_balance(accounts["CASH"]), 880)
        for _ in range(2):
            cancel_finance_document(self.site.id, self.store.id, "expense", expense.id, "Yanlış masraf kaydı")
        self.assertEqual(get_account_balance(accounts["CASH"]), 1000)
        self.assertEqual(expense.status, "approved")
        self.assertEqual(FinanceMovement.query.filter_by(reversal_of_id=expense.movement_id).count(), 1)

    def test_settled_card_collection_cannot_be_cancelled(self):
        self.activate()
        sale = Sale(site_id=self.site.id, store_id=self.store.id, document_no=3,
                    payment_method="Veresiye", total_amount=500, payment_status="OPEN")
        db.session.add(sale)
        db.session.flush()
        sync_sale_finance(sale)
        collection = collect_credit_sale_payment(site_id=self.site.id, store_id=self.store.id,
            sale_id=sale.id, payment_method="Kredi Kartı", amount=200, occurred_at=datetime.utcnow())
        pos = db.session.get(PosReconciliation, collection.pos_reconciliation_id)
        pos.status = "settled"
        db.session.flush()
        with self.assertRaisesRegex(ValueError, "Bankaya geçmiş"):
            cancel_finance_document(self.site.id, self.store.id, "collection", collection.id, "Yanlış tahsilat")
        self.assertEqual(credit_sale_remaining(sale), 300)
        self.assertEqual(FinanceMovement.query.filter(FinanceMovement.reversal_of_id.isnot(None)).count(), 0)

    def test_closed_day_and_request_security(self):
        accounts = self.activate()
        transfer = create_account_transfer(site_id=self.site.id, store_id=self.store.id,
            from_account_id=accounts["CASH"].id, to_account_id=accounts["BANK"].id,
            amount=200, occurred_at=datetime.utcnow())
        create_daily_closing(site_id=self.site.id, store_id=self.store.id, business_date=date.today(),
            counted_cash=800, counted_card=0, counted_transfer=200, handover_from="Test")
        db.session.commit()
        with self.assertRaisesRegex(ValueError, "kapatılmış"):
            cancel_finance_document(self.site.id, self.store.id, "transfer", transfer.id, "Yanlış transfer")
        client = self.app.test_client()
        self.assertEqual(client.post("/finance/operations/corrections", data={"kind": "transfer", "record_id": transfer.id}).status_code, 400)
        with patch("app.services.access_control.has_permission", return_value=False):
            for url in ("/finance/operations/corrections", "/payment-agenda", "/customer-history", "/slow-stock"):
                self.assertEqual(client.get(url).status_code, 403, url)

    def test_agenda_customer_identity_and_empty_pages(self):
        self.activate()
        for number, name, phone in ((1, "Aynı İsim", "05380000001"), (2, "Aynı İsim", "05380000002")):
            db.session.add(Sale(site_id=self.site.id, store_id=self.store.id, document_no=number,
                customer_name=name, customer_mobile=phone, payment_method="Veresiye", total_amount=100,
                payment_due_date=date.today(), payment_status="OPEN"))
        db.session.commit()
        history = customer_history(self.site.id, self.store.id, "05380000001")
        self.assertEqual(len(history["sales"]), 1)
        self.assertEqual(history["outstanding"], 100)
        self.assertEqual(len(due_agenda(self.site.id, self.store.id, date.today())), 2)
        self.assertEqual(due_agenda(self.site.id, 999, date.today()), [])
        client = self.app.test_client()
        for path in ("/payment-agenda", "/slow-stock", "/customer-history", "/finance/operations/corrections"):
            self.assertEqual(client.get(path).status_code, 200, path)

    def test_slow_stock_only_lists_old_positive_store_stock(self):
        product = Product(site_id=self.site.id, name="Eski Ürün", category="Test", barcode="OLD1",
            product_code="OLD1", purchase_price=100, created_at=datetime(2025, 1, 1))
        db.session.add(product)
        db.session.flush()
        db.session.add(StoreInventory(site_id=self.site.id, store_id=self.store.id, product_id=product.id,
            stock_quantity=2, created_at=datetime(2025, 1, 1)))
        db.session.flush()
        rows = slow_stock(self.site.id, self.store.id, date(2026, 10, 13))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cost"], 200)
        self.assertEqual(slow_stock(self.site.id, 999, date(2026, 10, 13)), [])


class BackupSafetyTests(unittest.TestCase):
    def test_backup_restores_to_isolated_file_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.db"
            with closing(sqlite3.connect(source)) as connection:
                connection.execute("CREATE TABLE products (name TEXT)")
                connection.execute("INSERT INTO products VALUES ('Test')")
                connection.commit()
            original = source.read_bytes()
            with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///" + source.as_posix(), "BACKUP_DIR": str(Path(folder) / "backups")}):
                destination = backup_database()
            manifest = json.loads(destination.with_suffix(".sqlite3.json").read_text())
            self.assertTrue(manifest["restore_tested"])
            self.assertEqual(len(manifest["sha256"]), 64)
            self.assertEqual(source.read_bytes(), original)
            with closing(sqlite3.connect(destination)) as connection:
                self.assertEqual(connection.execute("SELECT name FROM products").fetchone()[0], "Test")
