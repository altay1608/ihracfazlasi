from datetime import date, datetime
from decimal import Decimal
import unittest
from unittest.mock import patch
from sqlalchemy import event

import tests.test_finance_overview as fixture
from app.extensions import db
from app.models import Sale, SalePayment, FinanceMovement
from app.services.finance import sync_sale_finance, collect_credit_sale_payment, create_account_transfer, settle_auto_pos_reconciliation
from app.services.finance_corrections import cancel_finance_document
from app.services.finance_overview import build_money_overview, build_receipts_summary
from app.services.finance_operations import closing_expectations
from app.services.lobby_finance import build_lobby_finance


class CustomerReceiptsTests(unittest.TestCase):
    setUp = fixture.FinanceOverviewTests.setUp
    tearDown = fixture.FinanceOverviewTests.tearDown
    seed = fixture.FinanceOverviewTests.seed
    movement = fixture.FinanceOverviewTests.movement

    def sale(self, allocations, when=datetime(2026, 10, 20, 9)):
        sale = Sale(site_id=self.site.id, store_id=self.store.id, sale_date=when,
                    total_amount=sum(Decimal(value) for value in allocations.values()),
                    payment_method=next(iter(allocations)) if len(allocations) == 1 else 'Parçalı Ödeme',
                    customer_name='Test', payment_due_date=date(2026, 10, 25))
        for method, value in allocations.items():
            sale.payments.append(SalePayment(payment_method=method, amount=Decimal(value), status='OPEN' if method == 'Veresiye' else 'PAID'))
        db.session.add(sale)
        sync_sale_finance(sale)
        db.session.flush()
        return sale

    def collect(self, sale, method, amount, when):
        return collect_credit_sale_payment(site_id=self.site.id, store_id=self.store.id,
            sale_id=sale.id, payment_method=method, amount=Decimal(amount), occurred_at=when)

    def overview(self, day=20):
        return build_money_overview(self.site.id, self.store.id, date(2026, 10, 1), date(2026, 10, day))

    def test_credit_does_not_increase_cash_and_later_partial_payment_is_not_new_sale(self):
        self.seed()
        sale = self.sale({'Veresiye': '3850'})
        before = self.overview()
        self.assertEqual(before['period']['net_turnover'], 3850)
        self.assertEqual(before['receipts']['period']['total'], 0)
        self.assertEqual(before['cash_balance'], 0)
        self.assertEqual(before['credit_receivable'], 3850)
        self.assertEqual(closing_expectations(self.site.id, self.store.id, date(2026,10,20))['cash'], 0)
        self.collect(sale, 'Nakit', '850', datetime(2026,10,21,9))
        db.session.flush()
        after = self.overview(21)
        self.assertEqual(after['receipts']['period']['total'], 850)
        self.assertEqual(after['receipts']['last_day']['cash'], 850)
        self.assertEqual(after['credit_receivable'], 3000)
        self.assertEqual(after['cash_balance'], 850)
        self.assertEqual(after['period']['net_turnover'], 3850)
        self.assertEqual(build_receipts_summary(self.site.id,self.store.id,date(2026,10,20),date(2026,10,20))['period']['total'], 0)
        self.assertIn('Veresiye satış · para alınmadı', [r['title'] for r in build_lobby_finance(self.site.id,self.store.id,date(2026,10,21))['rows']])

    def test_split_and_card_collection_settlement_and_internal_transfer_not_counted_twice(self):
        self.seed()
        sale = self.sale({'Nakit':'500', 'Havale/EFT':'600', 'Kredi Kartı':'700', 'Veresiye':'800'})
        self.assertEqual(self.overview()['receipts']['period']['total'], 1800)
        collection = self.collect(sale, 'Kredi Kartı', '800', datetime(2026,10,21,9))
        db.session.flush()
        settle_auto_pos_reconciliation(site_id=self.site.id, store_id=self.store.id,
            reconciliation_id=collection.pos_reconciliation_id, settled_at=datetime(2026,10,22,9))
        create_account_transfer(site_id=self.site.id,store_id=self.store.id,
            from_account_id=self.accounts['CASH'].id,to_account_id=self.accounts['BANK'].id,
            amount=100,occurred_at=datetime(2026,10,22,10))
        db.session.flush()
        result = self.overview(22)
        self.assertEqual(result['receipts']['period'], {'cash':500,'bank':600,'card':1500,'total':2600,'credit_collections':800})
        self.assertEqual(result['receipts']['last_day']['total'], 0)
        self.assertEqual(result['period']['net_turnover'],2600)
        self.assertEqual(result['credit_receivable'],0)

    def test_prior_month_collection_reversal_keeps_original_month_and_negative_current_receipt(self):
        self.seed()
        sale = self.sale({'Veresiye':'1000'}, datetime(2026,9,20,9))
        collection = self.collect(sale, 'Havale/EFT', '400', datetime(2026,9,21,9))
        with patch('app.services.finance_corrections.datetime') as clock:
            clock.utcnow.return_value = datetime(2026,10,20,9)
            cancel_finance_document(self.site.id,self.store.id,'collection',collection.id,'Yanlış tahsilat')
        db.session.flush()
        result = self.overview()
        self.assertEqual(result['receipts']['period']['bank'], -400)
        self.assertEqual(result['receipts']['period']['credit_collections'], -400)
        self.assertEqual(result['period']['net_turnover'], 0)
        self.assertEqual(result['credit_receivable'], 1000)
        september = build_receipts_summary(self.site.id,self.store.id,date(2026,9,1),date(2026,9,30))
        self.assertEqual(september['period']['total'],400)

    def test_refunds_credit_offsets_expenses_and_openings_are_distinct(self):
        self.seed()
        self.movement('sale','in','1200')
        self.movement('sale','in','500','CREDIT')
        self.movement('return','out','200')
        self.movement('return','out','100','CREDIT')
        self.movement('return','out','300','BANK')
        self.movement('exchange_sale','in','400','BANK')
        for kind in ('manual','opening_balance','opening_adjustment','current_settlement','pos_reconciliation','transfer'):
            self.movement(kind,'in','999')
        result = self.overview()['receipts']['period']
        self.assertEqual(result,{'cash':1000,'bank':100,'card':0,'total':1100,'credit_collections':0})

    def test_istanbul_boundary_scope_constant_query_count_and_no_writes(self):
        self.seed()
        self.movement('sale','in','10',when=datetime(2026,9,30,20,59))
        self.movement('sale','in','20',when=datetime(2026,9,30,21))
        self.movement('sale','in','30',when=datetime(2026,10,1,21))
        db.session.add(FinanceMovement(site_id=self.site.id, store_id=self.store.id+1,
            account_id=self.accounts['CASH'].id, category_id=self.category.id,
            occurred_at=datetime(2026,10,1,9), direction='in',amount=900,
            movement_type='sale',source_type='test',source_key='other-store'))
        db.session.flush()
        before = FinanceMovement.query.count()
        queries=[]
        def record(*args): queries.append(args[2])
        event.listen(db.engine,'before_cursor_execute',record)
        try:
            summary=build_receipts_summary(self.site.id,self.store.id,date(2026,10,1),date(2026,10,1))
        finally: event.remove(db.engine,'before_cursor_execute',record)
        self.assertEqual(summary['period']['total'],20)
        self.assertEqual(len(queries),1)
        self.assertEqual(FinanceMovement.query.count(),before)
        self.assertFalse(db.session.new)
        self.assertFalse(db.session.dirty)

    def test_finance_and_lobby_render_separate_receipts_and_balances(self):
        self.seed()
        self.sale({'Veresiye':'3850'})
        db.session.commit()
        client=self.app.test_client()
        with client.session_transaction() as state:
            state['active_site_id']=self.site.id
            state['active_store_id']=self.store.id
        for url,expected in [('/finance/operations/?month=2026-10','Net tahsil edilen'),('/', 'Satış ve Tahsilat Ayrı')]:
            response=client.get(url)
            self.assertEqual(response.status_code,200,response.get_data(as_text=True))
            self.assertIn(expected,response.get_data(as_text=True))
            self.assertIn('Bekleyen veresiye',response.get_data(as_text=True))
