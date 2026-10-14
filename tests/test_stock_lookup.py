import unittest
from unittest.mock import patch
import test_finance as fixture
from app.extensions import db
from app.models import Product, ProductBarcode, StoreInventory, Store, Sale, FinanceMovement
from app.services.product_inventory import sync_product_barcodes


class StockLookupTests(unittest.TestCase):
    setUp = fixture.FinanceModuleTests.setUp
    tearDown = fixture.FinanceModuleTests.tearDown

    def prepare(self):
        product = Product(site_id=self.site.id, name='Telefon Test Ürünü', category='Tişört',
                          product_code='LOOKUP1', barcode='LOOKUP1', variant='M',
                          purchase_price=123, sale_price=500, barcode_mode='unit')
        db.session.add(product)
        db.session.flush()
        sync_product_barcodes(product, 2)
        db.session.commit()
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['active_site_id'] = self.site.id
            session['active_store_id'] = self.store.id
        return client, product

    def test_lookup_is_read_only_and_accepts_unit_or_product_code(self):
        client, product = self.prepare()
        before = (product.stock_quantity, ProductBarcode.query.count(), Sale.query.count(), FinanceMovement.query.count())
        for code in [product.product_code, product.product_barcodes[0].barcode]:
            response = client.get('/products/stock-lookup', query_string={'barcode': code})
            self.assertEqual(response.status_code, 200)
            self.assertIn('Telefon Test Ürünü', response.get_data(as_text=True))
            self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertEqual(before, (product.stock_quantity, ProductBarcode.query.count(), Sale.query.count(), FinanceMovement.query.count()))
        self.assertEqual(client.post('/products/stock-lookup').status_code, 405)

    def test_sold_unit_is_visible_and_unknown_code_is_safe(self):
        client, product = self.prepare()
        product.product_barcodes[0].status = 'sold'
        db.session.commit()
        response = client.get('/products/stock-lookup', query_string={'barcode': product.product_barcodes[0].barcode})
        self.assertIn('Satılmış', response.get_data(as_text=True))
        response = client.get('/products/stock-lookup', query_string={'barcode': '<script>alert(1)</script>'})
        self.assertNotIn('<script>alert(1)</script>', response.get_data(as_text=True))
        self.assertIn('ürün bulunamadı', response.get_data(as_text=True))

    def test_other_store_stock_is_not_exposed(self):
        client, product = self.prepare()
        other = Store(site_id=self.site.id, code='OTHER', name='Diğer')
        db.session.add(other)
        db.session.commit()
        with client.session_transaction() as session:
            session['active_store_id'] = other.id
        response = client.get('/products/stock-lookup', query_string={'barcode': product.product_code})
        self.assertNotIn('Telefon Test Ürünü', response.get_data(as_text=True))

    def test_no_product_permission_denies_page(self):
        client, _ = self.prepare()
        with patch('app.services.access_control.has_permission', return_value=False):
            self.assertEqual(client.get('/products/stock-lookup').status_code, 403)

    def test_hidden_columns_are_not_rendered(self):
        client, product = self.prepare()
        with patch('app.services.access_control.has_permission', side_effect=lambda key: not key.startswith('products.column.')):
            html = client.get('/products/stock-lookup', query_string={'barcode': product.product_code}).get_data(as_text=True)
        self.assertNotIn('Alış (KDV hariç)', html)
        self.assertNotIn('KDV dâhil satış:', html)


if __name__ == '__main__':
    unittest.main()
