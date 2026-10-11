import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from flask import session
from sqlalchemy import event

from app import create_app
from app.extensions import db
from app.models import Product, Return, ReturnItem, Sale, SaleItem, StoreInventory
from app.services.reporting import get_daily_turnover, get_dashboard_metrics, attach_stock_thresholds
from app.utils import istanbul_to_utc
from config import BaseConfig


class DashboardTurnoverTests(unittest.TestCase):
    def setUp(self):
        with patch.object(BaseConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"):
            self.app = create_app("development")
        self.app.config.update(TESTING=True, AUTH_ENABLED=False, AUDIT_LOGGING_ENABLED=False)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.product = Product(name="Test Ürün", category="Tişört", barcode="001", product_code="001", stock_quantity=1)
        db.session.add(self.product)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def sale(self, local_time, amount, *, store=1, site=1, status="DELIVERED", method="Nakit"):
        sale = Sale(
            site_id=site, store_id=store, sale_date=istanbul_to_utc(local_time),
            total_amount=Decimal(amount), payment_method=method, order_status=status,
        )
        db.session.add(sale)
        db.session.flush()
        return sale

    def refund(self, sale, local_time, amount, status="tamamlandi"):
        record = Return(
            site_id=sale.site_id, store_id=sale.store_id, original_sale_id=sale.id,
            return_date=istanbul_to_utc(local_time), reason="Test", type="iade", status=status,
        )
        record.items.append(ReturnItem(
            site_id=sale.site_id, store_id=sale.store_id, product_id=self.product.id,
            quantity=1, refund_amount=Decimal(amount) / Decimal("1.1"), gross_refund_amount=Decimal(amount),
            product_code_snapshot="001", product_name_snapshot="Test Ürün",
        ))
        db.session.add(record)
        db.session.flush()

    def test_turnover_local_midnight_discounts_refunds_exchange_credit_and_cancellation(self):
        old_sale = self.sale(datetime(2026, 9, 30, 23, 59), "400")
        first = self.sale(datetime(2026, 10, 1, 0, 1), "1800", method="Veresiye")
        first.total_discount = Decimal("200")  # already reflected in total_amount
        self.sale(datetime(2026, 10, 2, 23, 59), "100")
        self.sale(datetime(2026, 11, 1, 0, 0), "999")
        self.sale(datetime(2026, 10, 1, 10), "500", status="CANCELLED")
        self.sale(datetime(2026, 10, 1, 11), "0")  # gift/personal: no revenue
        self.refund(old_sale, datetime(2026, 10, 1, 1), "400")
        self.refund(first, datetime(2026, 10, 2, 10), "100")
        self.refund(first, datetime(2026, 10, 2, 10), "-50")  # exchange replacement
        self.refund(first, datetime(2026, 10, 2, 10), "500", status="iptal")
        db.session.commit()
        rows = get_daily_turnover(date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(len(rows), 31)
        self.assertEqual(rows[0]["revenue"], Decimal("1400.00"))
        self.assertEqual(rows[1]["revenue"], Decimal("50.00"))
        self.assertEqual(rows[2]["revenue"], Decimal("0.00"))
        self.assertEqual(sum(row["revenue"] for row in rows), Decimal("1450.00"))

    def test_turnover_is_tenant_and_store_scoped(self):
        own = self.sale(datetime(2026, 10, 1), "100", site=1, store=1)
        other_store = self.sale(datetime(2026, 10, 1), "900", site=1, store=2)
        other_site = self.sale(datetime(2026, 10, 1), "800", site=2, store=3)
        for sale in (own, other_store, other_site):
            self.refund(sale, datetime(2026, 10, 1, 1), "10")
        db.session.commit()
        with self.app.test_request_context("/"):
            session.update(auth_user="test", active_site_id=1, active_store_id=1)
            self.assertEqual(get_daily_turnover(date(2026, 10, 1), date(2026, 10, 1))[0]["revenue"], Decimal("90.00"))

    def test_turnover_uses_two_queries_without_loading_product_graph(self):
        for day in range(1, 29):
            self.sale(datetime(2026, 10, day, 10), "123")
        db.session.commit()
        db.session.remove()
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        event.listen(db.engine, "before_cursor_execute", record)
        try:
            rows = get_daily_turnover(date(2026, 10, 1), date(2026, 10, 31))
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        self.assertEqual(len(statements), 2)
        self.assertEqual(sum(row["revenue"] for row in rows), Decimal("3444.00"))
        self.assertNotIn("product_barcodes", " ".join(statements))

    def test_dashboard_five_days_cross_month_and_current_month_total(self):
        self.sale(datetime(2026, 9, 30, 12), "500")
        self.sale(datetime(2026, 10, 1, 12), "100")
        db.session.commit()
        with patch("app.modules.dashboard.routes.now_in_istanbul", return_value=datetime(2026, 10, 2, 12)):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Son 5 Günün Cirosu", html)
        self.assertIn("28.09.2026", html)
        self.assertIn("02.10.2026", html)
        self.assertIn("<th>₺100,00</th>", html)
        for text in ("Alarm Yığını", "Düşük Stoklu Ürünler", "Alarm Var", "Stok Sağlığı", "Stok Radarı"):
            self.assertNotIn(text, html)

    def test_report_leap_year_zero_days_invalid_month_and_permissions(self):
        response = self.client.get("/reports/turnover?month=2024-02")
        self.assertEqual(response.status_code, 200)
        self.assertIn("29.02.2024", response.get_data(as_text=True))
        self.assertNotIn("30.02.2024", response.get_data(as_text=True))
        for invalid in ("oops", "2026-13", "0000-01", "9999-12"):
            self.assertEqual(self.client.get(f"/reports/turnover?month={invalid}").status_code, 400)
        with self.client.session_transaction() as state:
            state["auth_user"] = "test"
        with patch("app.services.access_control.has_permission", return_value=False):
            self.assertEqual(self.client.get("/reports/turnover").status_code, 403)
        self.assertEqual(self.product.stock_quantity, 1)

    def test_stock_only_dashboard_does_not_query_finance_or_alarms(self):
        with patch("app.modules.dashboard.routes.has_permission", return_value=False), patch(
            "app.services.access_control.has_permission", side_effect=lambda code: code in {"dashboard.access", "dashboard.column.stock"}
        ), patch("app.modules.dashboard.routes.get_daily_turnover") as turnover, patch(
            "app.modules.dashboard.routes.get_dashboard_metrics"
        ) as metrics:
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Son 5 Günün Cirosu", response.get_data(as_text=True))
        turnover.assert_not_called()
        metrics.assert_not_called()

    def test_dashboard_metrics_midnight_and_no_unused_relationship_queries(self):
        sale = self.sale(datetime(2026, 10, 1, 0, 1), "110")
        sale.items.append(SaleItem(product=self.product, quantity=1, unit_price=Decimal("100")))
        db.session.commit()
        db.session.remove()
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        event.listen(db.engine, "before_cursor_execute", record)
        try:
            metrics = get_dashboard_metrics(date(2026, 10, 1))
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        self.assertEqual(metrics["revenue"], Decimal("110.00"))
        self.assertEqual(metrics["total_sales"], 1)
        for unused in ("product_barcodes", "store_inventories", "sale_payments", "credit_sale_collections"):
            self.assertNotIn(unused, " ".join(statements))

    def test_empty_category_map_does_not_query_once_per_product(self):
        with patch("app.services.reporting.build_category_threshold_map", return_value={}) as categories:
            attach_stock_thresholds([self.product] * 224, 0)
        categories.assert_called_once()

    def test_inventory_filters_before_loading_and_preserves_stock(self):
        sold = Product(name="Tükenmiş Ürün", category="Tişört", barcode="002", product_code="002", stock_quantity=0)
        foreign = Product(name="Diğer Mağaza", category="Tişört", barcode="003", product_code="003")
        foreign.store_inventories.append(StoreInventory(site_id=1, store_id=2, stock_quantity=10))
        db.session.add_all([sold, foreign])
        db.session.commit()
        from app.modules.products.routes import get_products_listing
        with self.app.test_request_context("/products/"):
            rows, _, _ = get_products_listing()
            self.assertEqual([row.name for row in rows], ["Test Ürün"])
        response = self.client.get("/products/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("stock-status-low", response.get_data(as_text=True))
        self.assertNotIn("Düşük Stok", response.get_data(as_text=True))
        with self.app.test_request_context("/products/?stock=out"):
            rows, _, _ = get_products_listing()
            self.assertEqual({row.name for row in rows}, {"Tükenmiş Ürün", "Diğer Mağaza"})
        self.assertEqual(Product.query.count(), 3)
        self.assertEqual(StoreInventory.query.filter_by(store_id=2).one().stock_quantity, 10)


if __name__ == "__main__":
    unittest.main()
