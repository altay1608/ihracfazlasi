import unittest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
import tests.test_finance as fixture
from app.extensions import db
from app.models import FinanceMovement, FinanceAccount, FinanceCategory, Store
from app.services.finance import activate_finance
from app.services.finance_overview import build_money_overview


class FinanceOverviewTests(unittest.TestCase):
    setUp = fixture.FinanceModuleTests.setUp
    tearDown = fixture.FinanceModuleTests.tearDown

    def seed(self):
        activate_finance(self.site.id, self.store.id, activated_at=datetime(2026, 9, 1))
        db.session.flush()
        self.accounts = {a.code: a for a in FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id)}
        self.category = FinanceCategory.query.filter_by(site_id=self.site.id, code='MANUAL_OUT').one()

    def movement(self, kind, direction, amount, code='CASH', when=None, reversal=None):
        row = FinanceMovement(site_id=self.site.id, store_id=self.store.id,
            account_id=self.accounts[code].id, category_id=self.category.id,
            occurred_at=when or datetime(2026, 10, 20, 9), direction=direction,
            amount=Decimal(amount), movement_type=kind, source_type='test', source_key=uuid4().hex,
            reversal_of_id=reversal.id if reversal else None)
        db.session.add(row)
        db.session.flush()
        return row

    def test_balances_period_payments_reversals_and_transfers_are_separate(self):
        self.seed()
        self.movement('sale','in','1000')
        self.movement('sale','in','500','CREDIT')
        self.movement('sale','in','200','POS')
        self.movement('return','out','100')
        self.movement('transfer','out','300')
        self.movement('transfer','in','300','BANK')
        self.movement('current_settlement','out','150','BANK')
        expense=self.movement('manual','out','80')
        self.movement('reversal','in','80', reversal=expense)
        self.movement('manual','out','20')
        self.movement('pos_commission','out','5','POS')
        self.movement('obligation_payment','out','30')
        self.movement('opening_balance','in','50',when=datetime(2026,9,20))
        before=FinanceMovement.query.count()
        result=build_money_overview(self.site.id,self.store.id,date(2026,10,1),date(2026,10,29))
        self.assertEqual(result['period']['net_turnover'],Decimal('1600'))
        self.assertEqual(result['period']['payments_total'],Decimal('205'))
        self.assertEqual(result['period']['manual_outflows'],Decimal('20'))
        self.assertEqual(result['period']['transfer_net'],0)
        self.assertEqual(result['credit_receivable'],Decimal('500'))
        self.assertEqual(result['pos_receivable'],Decimal('195'))
        self.assertEqual(result['available_money'],Decimal('750'))
        self.assertEqual(result['total_balance'],Decimal('1445'))
        self.assertEqual(FinanceMovement.query.count(),before)
        self.assertFalse(db.session.new)
        self.assertFalse(db.session.dirty)

    def test_month_boundary_in_istanbul_and_other_store_isolation(self):
        self.seed()
        self.movement('sale','in','10',when=datetime(2026,9,30,20,59))
        self.movement('sale','in','20',when=datetime(2026,9,30,21,0))
        other=Store(site_id=self.site.id,code='OTHER',name='Other')
        db.session.add(other);db.session.flush()
        activate_finance(self.site.id,other.id,opening_cash=Decimal('999'))
        db.session.flush()
        result=build_money_overview(self.site.id,self.store.id,date(2026,10,1),date(2026,10,1))
        self.assertEqual(result['period']['net_turnover'],20)
        self.assertEqual(result['available_money'],30)
        self.accounts['CASH'].is_active=False
        db.session.flush()
        self.assertEqual(build_money_overview(self.site.id,self.store.id,date(2026,10,1),date(2026,10,1))['available_money'],30)

    def test_business_card_is_not_available_money_and_empty_period_is_zero(self):
        self.seed()
        self.movement('manual','out','250','BIZ_CARD')
        result=build_money_overview(self.site.id,self.store.id,date(2026,9,1),date(2026,9,30))
        self.assertEqual(result['available_money'],0)
        self.assertEqual(result['business_card_debt'],250)
        self.assertEqual(result['period']['payments_total'],0)

    def test_finance_pages_render_and_do_not_change_ledger(self):
        self.seed()
        self.movement('sale','in','100')
        from app.services.finance import create_current_account, create_current_entry
        supplier=create_current_account(site_id=self.site.id, account_category='supplier', name='Test Toptancı')
        entry=create_current_entry(site_id=self.site.id,store_id=self.store.id,current_account_id=supplier.id,entry_type='payable',amount=300)
        db.session.commit()
        before=[(r.id,r.amount,r.direction) for r in FinanceMovement.query.order_by(FinanceMovement.id)]
        with self.app.test_client() as client:
            with client.session_transaction() as state:
                state['active_site_id']=self.site.id
                state['active_store_id']=self.store.id
                state['auth_csrf_token']='test-token'
            for path in ('/finance/operations/','/finance/operations/?month=2026-09','/finance/current-accounts','/finance/operations/expenses','/finance/transfers','/finance/manual','/finance/'):
                response=client.get(path)
                self.assertEqual(response.status_code,200,path)
                html=response.get_data(as_text=True)
                self.assertIn('Para Hareketleri',html)
                if path=='/finance/current-accounts':
                    self.assertIn('Ödemeyi kaydet',html)
                    self.assertIn('Test Toptancı',html)
                    self.assertIn('name="csrf_token"',html)
                    self.assertIn('max="300.00"',html)
                if path=='/finance/operations/expenses':
                    from html.parser import HTMLParser
                    class Options(HTMLParser):
                        def __init__(self): super().__init__(); self.category=False; self.values=[]
                        def handle_starttag(self, tag, attrs):
                            attrs=dict(attrs)
                            if tag=='select': self.category=attrs.get('name')=='category_id'
                            if tag=='option' and self.category: self.values.append(attrs.get('value'))
                        def handle_endtag(self,tag):
                            if tag=='select': self.category=False
                    options=Options();options.feed(html)
                    self.assertEqual(options.values,[str(self.category.id)])
        after=[(r.id,r.amount,r.direction) for r in FinanceMovement.query.order_by(FinanceMovement.id)]
        self.assertEqual(before,after)

if __name__=='__main__': unittest.main()
