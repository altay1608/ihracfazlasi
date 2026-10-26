import unittest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch
import test_finance as fixture
from app.extensions import db
from app.models import Product, Sale, FinanceAccount
from app.services.finance import activate_finance, get_account_balance
from app.services.product_inventory import sync_product_barcodes


class NoProfitFloorTests(unittest.TestCase):
    setUp = fixture.FinanceModuleTests.setUp
    tearDown = fixture.FinanceModuleTests.tearDown

    def test_discounted_sale_and_edit_need_no_profit_confirmation(self):
        activate_finance(self.site.id, self.store.id, activated_at=datetime.utcnow() - timedelta(minutes=1))
        product = Product(name="Test Tişört", category="Tişört", product_code="P1", barcode="P1",
            sale_price=2000, purchase_price=1000, barcode_mode="shared")
        db.session.add(product)
        db.session.flush()
        sync_product_barcodes(product, 3)
        db.session.commit()
        product_id = product.id
        client = self.app.test_client()
        with client.session_transaction() as session:
            session["auth_csrf_token"] = "test-token"
        payload = {"payment_method": "Nakit", "target_final_total": 1500,
                   "items": [{"product_id": product_id, "quantity": 1, "unit_price": 2000}]}
        headers = {"X-CSRFToken": "test-token"}
        with patch("app.modules.sales.routes.Sale", side_effect=lambda **kw: Sale(site_id=self.site.id, store_id=self.store.id, **kw)):
            response = client.post("/sales/complete", json=payload, headers=headers)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(Sale.query.count(), 1)
        self.assertEqual(db.session.get(Product, product_id).stock_quantity, 2)
        cash = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code="CASH").one()
        self.assertEqual(get_account_balance(cash), Decimal("1500"))
        sale_id = Sale.query.one().id
        # Even a below-cost price remains the user's decision; accounting keeps actual amounts.
        payload["target_final_total"] = 500
        response = client.post(f"/sales/{sale_id}/update", json=payload, headers=headers)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(db.session.get(Sale, sale_id).total_amount, Decimal("500"))
        self.assertEqual(get_account_balance(cash), Decimal("500"))
        self.assertEqual(db.session.get(Product, product_id).stock_quantity, 2)
        self.assertEqual(Sale.query.count(), 1)
