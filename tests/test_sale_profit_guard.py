import unittest
from decimal import Decimal
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
import test_finance as fixture
from app.extensions import db
from app.models import Product, Sale, FinanceMovement, FinanceAccount
from app.services.finance import activate_finance, get_account_balance
from app.services.product_inventory import sync_product_barcodes
from app.services.sale_profit_guard import profit_warnings


def line(price, cost=1000, quantity=1, kind="sale", discount=0):
    return SimpleNamespace(unit_price=Decimal(str(price)), quantity=quantity,
        discount_amount=Decimal(str(discount)), line_type=kind,
        product=SimpleNamespace(id=1, name="Test", variant="M", purchase_price=Decimal(str(cost))))


class ProfitMathTests(unittest.TestCase):
    def test_threshold_includes_vat_and_equality_is_allowed(self):
        self.assertEqual(profit_warnings([line(2100)], Decimal("2310"), Decimal("1.10")), [])
        rows = profit_warnings([line(2100)], Decimal("2309.99"), Decimal("1.10"))
        self.assertEqual(rows[0]["minimum_total"], "2310.00")

    def test_basket_discount_is_proportional_not_averaged_profit(self):
        rows = profit_warnings([line(3000, 1500), line(2000, 1000)], Decimal("4950"), Decimal("1.10"))
        self.assertEqual([Decimal(row["charged_total"]) for row in rows], [Decimal("2970"), Decimal("1980")])

    def test_quantity_line_discount_and_excluded_types(self):
        items = [line(2500, quantity=2, discount=1000), line(3000, kind="gift"), line(4000, kind="personal")]
        rows = profit_warnings(items, Decimal("4400"), Decimal("1.10"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["minimum_total"], "4620.00")
        self.assertEqual(profit_warnings(items[1:], Decimal("0"), Decimal("1.10")), [])

    def test_penny_allocation_and_zero_price(self):
        rows = profit_warnings([line(1), line(1), line(1)], Decimal("1"), Decimal("1.10"))
        self.assertEqual(sum(Decimal(row["charged_total"]) for row in rows), 1)
        self.assertEqual(profit_warnings([line(0)], Decimal("0"), Decimal("1.10"))[0]["charged_total"], "0")


class ProfitRouteTests(unittest.TestCase):
    setUp = fixture.FinanceModuleTests.setUp
    tearDown = fixture.FinanceModuleTests.tearDown

    def test_warning_rolls_back_stock_then_confirmation_saves_once(self):
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
        initial_movements = FinanceMovement.query.count()
        payload = {"payment_method": "Nakit", "target_final_total": 2000,
                   "items": [{"product_id": product_id, "quantity": 1, "unit_price": 2000}]}
        headers = {"X-CSRFToken": "test-token"}
        # AUTH_ENABLED=False bypasses the production tenant-assignment hook.
        def complete():
            with patch("app.modules.sales.routes.Sale", side_effect=lambda **kw: Sale(site_id=self.site.id, store_id=self.store.id, **kw)):
                return client.post("/sales/complete", json=payload, headers=headers)
        response = complete()
        self.assertEqual(response.status_code, 409, response.get_data(as_text=True))
        self.assertEqual(response.json["code"], "profit_confirmation_required")
        self.assertEqual(Sale.query.count(), 0)
        self.assertEqual(FinanceMovement.query.count(), initial_movements)
        self.assertEqual(db.session.get(Product, product_id).stock_quantity, 3)
        payload["profit_warning_confirmed"] = True
        response = complete()
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(Sale.query.count(), 1)
        self.assertEqual(db.session.get(Product, product_id).stock_quantity, 2)
        cash = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code="CASH").one()
        self.assertEqual(get_account_balance(cash), Decimal("2000"))
        sale = Sale.query.one()
        sale_id = sale.id
        payload.pop("profit_warning_confirmed")
        payload["target_final_total"] = 1900
        response = client.post(f"/sales/{sale_id}/update", json=payload, headers=headers)
        self.assertEqual(response.status_code, 409, response.get_data(as_text=True))
        self.assertEqual(db.session.get(Sale, sale_id).total_amount, Decimal("2000"))
        self.assertEqual(get_account_balance(cash), Decimal("2000"))
        self.assertEqual(db.session.get(Product, product_id).stock_quantity, 2)
