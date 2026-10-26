import re
import html
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
import test_finance as fixture
from app.extensions import db
from app.models import Product, Sale, SaleItem, Return, ReturnSettlement, FinanceAccount, FinanceMovement
from app.services.finance import (activate_finance, sync_sale_finance, get_account_balance,
    credit_sale_remaining, create_current_account, create_current_entry, sync_return_finance)
from app.services.product_inventory import sync_product_barcodes, reserve_barcodes_for_sale
from app.services.customer_orders import prepare_customer_order
from app.services.reference_data import get_return_reason_choices
from app.services.return_settlement import settlement_plan, post_settlement, resolve_debt


class ReturnSettlementTests(unittest.TestCase):
    setUp = fixture.FinanceModuleTests.setUp
    tearDown = fixture.FinanceModuleTests.tearDown

    def setup_sale(self, method='Nakit'):
        activate_finance(self.site.id, self.store.id, opening_cash=2000, activated_at=datetime.utcnow()-timedelta(days=1))
        product = Product(site_id=self.site.id, name='İade Test', category='Tişört', product_code='R1', barcode='R1',
            purchase_price=100, sale_price=200, barcode_mode='unit')
        db.session.add(product)
        db.session.flush()
        sync_product_barcodes(product, 1)
        sale = Sale(site_id=self.site.id, store_id=self.store.id, payment_method=method,
            customer_mobile='05384793696', total_amount=220, total_discount=0)
        item = SaleItem(site_id=self.site.id, store_id=self.store.id, product=product, quantity=1, unit_price=200)
        sale.items.append(item)
        prepare_customer_order(sale)
        db.session.add(sale)
        db.session.flush()
        code = product.product_barcodes[0]
        reserve_barcodes_for_sale(product, item, 1, [code.barcode])
        sync_sale_finance(sale)
        db.session.commit()
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['auth_csrf_token'] = 'test'
            session['active_site_id'] = self.site.id
            session['active_store_id'] = self.store.id
        self.app.config['WTF_CSRF_ENABLED'] = False
        data = dict(original_sale_id=str(sale.document_no), type='iade', reason=get_return_reason_choices()[0][0],
            note='', payment_method='Nakit', debt_target='', csrf_token='test')
        data[f'return_barcode_{item.id}_{code.id}'] = code.barcode
        self.sale, self.product, self.client, self.data = sale, product, client, data
        self.cash = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code='CASH').one()

    def preview(self):
        response = self.client.post('/returns/create', data=self.data, headers={'X-Requested-With': 'XMLHttpRequest', 'X-Modal-Request': '1', 'X-CSRFToken': 'test'})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        text = response.json['html']
        self.assertIn('henüz kaydedilmedi', text)
        token = re.search(r'name="settlement_confirmation" value="([^"]+)"', text).group(1)
        self.data['settlement_confirmation'] = html.unescape(token)
        return text

    def submit(self):
        return self.client.post('/returns/create', data=self.data, headers={'X-Requested-With': 'XMLHttpRequest', 'X-Modal-Request': '1', 'X-CSRFToken': 'test'})

    def test_cash_refund_preview_does_not_mutate_then_posts_once(self):
        self.setup_sale()
        movements = FinanceMovement.query.count()
        self.preview()
        self.assertEqual(Return.query.count(), 0)
        self.assertEqual(FinanceMovement.query.count(), movements)
        self.assertEqual(self.product.stock_quantity, 0)
        response = self.submit()
        self.assertTrue(response.json['success'], response.get_data(as_text=True))
        self.assertEqual(self.product.stock_quantity, 1)
        self.assertEqual(get_account_balance(self.cash), 2000)
        self.assertEqual(ReturnSettlement.query.one().cash_amount, 220)
        sync_return_finance(Return.query.one())
        db.session.commit()
        self.assertEqual(get_account_balance(self.cash), 2000)

    def test_credit_refund_reduces_receivable_not_cash(self):
        self.setup_sale('Veresiye')
        self.data['debt_target'] = f'sale:{self.sale.id}'
        self.data['payment_method'] = ''
        self.preview()
        response = self.submit()
        self.assertTrue(response.json['success'], response.get_data(as_text=True))
        self.assertEqual(credit_sale_remaining(self.sale), 0)
        self.assertEqual(get_account_balance(self.cash), 2000)
        self.assertEqual(ReturnSettlement.query.one().credit_amount, 220)
        credit = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code='CREDIT').one()
        self.assertEqual(get_account_balance(credit), 0)

    def test_manual_debt_and_excess_refund(self):
        self.setup_sale()
        customer = create_current_account(site_id=self.site.id, account_category='customer', name='Müşteri', phone='05384793696')
        entry = create_current_entry(site_id=self.site.id, store_id=self.store.id, current_account_id=customer.id, entry_type='receivable', amount=100)
        db.session.commit()
        self.data['debt_target'] = f'entry:{entry.id}'
        self.preview()
        response = self.submit()
        self.assertTrue(response.json['success'], response.get_data(as_text=True))
        self.assertEqual(entry.remaining_amount, 0)
        self.assertEqual(ReturnSettlement.query.one().cash_amount, 120)
        self.assertEqual(get_account_balance(self.cash), 2100)

    def test_wrong_customer_rejected_and_changed_amount_requires_new_preview(self):
        self.setup_sale()
        customer = create_current_account(site_id=self.site.id, account_category='customer', name='Başka', phone='05000000000')
        entry = create_current_entry(site_id=self.site.id, store_id=self.store.id, current_account_id=customer.id, entry_type='receivable', amount=100)
        db.session.commit()
        with self.assertRaises(ValueError):
            resolve_debt(self.sale, f'entry:{entry.id}')
        self.preview()
        self.data['payment_method'] = 'Havale/EFT'
        response = self.submit()
        self.assertFalse(response.json['success'])
        self.assertEqual(Return.query.count(), 0)

    def test_exchange_difference_directions(self):
        self.setup_sale()
        plan, _ = settlement_plan(self.sale, Decimal('220'), Decimal('330'), '', 'Nakit')
        self.assertEqual(plan['cash'], '-110.00')
        plan, _ = settlement_plan(self.sale, Decimal('220'), Decimal('220'), '', '')
        self.assertEqual(plan['cash'], '0.00')
        with self.assertRaises(ValueError):
            settlement_plan(self.sale, Decimal('220'), Decimal('330'), f'sale:{self.sale.id}', 'Nakit')

    def test_exchange_posts_net_collection_and_moves_both_stocks(self):
        self.setup_sale()
        replacement = Product(site_id=self.site.id, name='Yeni Ürün', category='Tişört', product_code='R2', barcode='R2',
            purchase_price=100, sale_price=300, barcode_mode='unit')
        db.session.add(replacement)
        db.session.flush()
        sync_product_barcodes(replacement, 1)
        db.session.commit()
        selected = next(key for key in self.data if key.startswith('return_barcode_'))
        self.data['replacement_barcode_' + selected.removeprefix('return_barcode_')] = replacement.product_barcodes[0].barcode
        self.data['type'] = 'degisim'
        self.preview()
        response = self.submit()
        self.assertTrue(response.json['success'], response.get_data(as_text=True))
        self.assertEqual(ReturnSettlement.query.one().cash_amount, -110)
        self.assertEqual(get_account_balance(self.cash), 2330)
        self.assertEqual(self.product.stock_quantity, 1)
        self.assertEqual(replacement.stock_quantity, 0)

    def test_unfunded_refund_rolls_back_stock_and_return(self):
        self.setup_sale()
        self.data['payment_method'] = 'Havale/EFT'
        self.preview()
        movements = FinanceMovement.query.count()
        response = self.submit()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json['success'])
        self.assertEqual(Return.query.count(), 0)
        self.assertEqual(ReturnSettlement.query.count(), 0)
        self.assertEqual(FinanceMovement.query.count(), movements)
        self.assertEqual(self.product.stock_quantity, 0)
