from datetime import date, datetime
from decimal import Decimal
import unittest
from unittest.mock import patch
from flask import render_template
from app.extensions import db
from app.models import FinanceMovement, DailyCashClosing, PosReconciliation
from app.services.finance import settle_auto_pos_reconciliation, get_account_balance
from app.services.finance_operations import create_daily_closing
from app.services.store_tools import customer_history
from app.services.finance_corrections import cancel_finance_document
from tests.test_customer_receipts import CustomerReceiptsTests

class MoneyControlsTests(unittest.TestCase):
    setUp = CustomerReceiptsTests.setUp
    tearDown = CustomerReceiptsTests.tearDown
    seed = CustomerReceiptsTests.seed
    sale = CustomerReceiptsTests.sale
    collect = CustomerReceiptsTests.collect

    def test_cash_difference_needs_reason_without_changing_ledger(self):
        self.seed()
        before = FinanceMovement.query.count()
        args = dict(site_id=self.site.id, store_id=self.store.id, business_date=date(2026,10,20),
                    counted_cash=10, counted_card=0, counted_transfer=0, handover_from='Test')
        with self.assertRaisesRegex(ValueError, 'Farkın nedenini'):
            create_daily_closing(**args)
        self.assertEqual(DailyCashClosing.query.count(), 0)
        row = create_daily_closing(**args, note='Sayım fazlası bulundu')
        self.assertEqual(row.cash_difference, 10)
        self.assertEqual(FinanceMovement.query.count(), before)
        db.session.flush()
        with self.assertRaisesRegex(ValueError, 'zaten'):
            create_daily_closing(**args, note='Tekrar deneme')

    def test_bank_mismatch_does_not_post_and_match_posts_once(self):
        self.seed()
        sale = self.sale({'Kredi Kartı':'1000'})
        pos = PosReconciliation.query.filter_by(sale_id=sale.id).one()
        before = FinanceMovement.query.count()
        args = dict(site_id=self.site.id, store_id=self.store.id, reconciliation_id=pos.id,
                    settled_at=datetime(2026,10,21,9))
        with self.assertRaisesRegex(ValueError, 'uyuşmuyor'):
            settle_auto_pos_reconciliation(**args, actual_amount=pos.net_amount-1)
        self.assertEqual(pos.status, 'pending')
        self.assertEqual(FinanceMovement.query.count(), before)
        self.assertEqual(get_account_balance(self.accounts['BANK']), 0)
        settle_auto_pos_reconciliation(**args, actual_amount=pos.net_amount)
        db.session.flush()
        self.assertEqual(get_account_balance(self.accounts['BANK']), pos.net_amount)
        with self.assertRaisesRegex(ValueError, 'sonuçlandırılmış'):
            settle_auto_pos_reconciliation(**args, actual_amount=pos.net_amount)

    def test_customer_payments_cancelled_and_identity(self):
        self.seed()
        sale = self.sale({'Veresiye':'1000'})
        sale.customer_mobile = '05550000001'
        other = self.sale({'Veresiye':'800'})
        other.customer_mobile = '05550000002'
        payment = self.collect(sale, 'Nakit','200',datetime(2026,10,21,9))
        db.session.flush()
        history = customer_history(self.site.id,self.store.id,'05550000001', 'Test')
        self.assertEqual(history['outstanding'],800)
        self.assertEqual(history['credit_collected'],200)
        self.assertEqual(len(history['sales']),1)
        self.assertEqual(len(history['candidates']),2)
        cancel_finance_document(self.site.id,self.store.id,'collection',payment.id,'Yanlış tahsilat')
        db.session.flush()
        history = customer_history(self.site.id,self.store.id,'05550000001')
        self.assertEqual(history['outstanding'],1000)
        self.assertTrue(history['collections'][0]['cancelled'])
        with self.app.test_request_context('/'):
            html=render_template('dashboard/customer_history.html',phone='05550000001',**history)
            self.assertIn('Veresiye Ödeme Geçmişi',html)
        self.assertEqual(customer_history(self.site.id,999,'05550000001')['sales'], [])

    def test_pages_render(self):
        self.seed()
        client = self.app.test_client()
        for path in ['/customer-history','/finance/pos-reconciliations','/finance/operations/daily-closing']:
            self.assertEqual(client.get(path).status_code,200,path)
