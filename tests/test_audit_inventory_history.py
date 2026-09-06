import unittest
from decimal import Decimal
from pathlib import Path
import re

from app import create_app
from app.extensions import db
from app.models import AuditLog, InventoryTransaction, Product, SystemSetting
from app.modules.audit.routes import AUDITABLE_ENDPOINT_LABELS
from app.services.audit_trail import (
    get_paused_audit_endpoints,
    set_audit_endpoint_paused,
)
from app.services.inventory_history import record_inventory_movement
from config import BaseConfig, config


class AuditAndInventoryHistoryTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / "_audit_inventory_history_test.db"
        self.database_path.unlink(missing_ok=True)

        class AuditHistoryTestConfig(BaseConfig):
            TESTING = True
            AUTH_ENABLED = False
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path}"
            AUTH_SETTINGS_PATH = str(self.database_path.with_suffix(".auth.json"))

        self.config_key = "audit_inventory_history_test"
        config[self.config_key] = AuditHistoryTestConfig
        self.app = create_app(self.config_key)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            self.product = Product(
                name="Test Urun",
                category="Test",
                barcode="TEST-URUN-001",
                product_code="TEST-001",
                purchase_price=Decimal("125.00"),
                sale_price=Decimal("250.00"),
                stock_quantity=5,
            )
            db.session.add(self.product)
            db.session.commit()
            self.product_id = self.product.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        config.pop(self.config_key, None)
        self.database_path.unlink(missing_ok=True)
        self.database_path.with_suffix(".auth.json").unlink(missing_ok=True)

    def test_inventory_movement_snapshots_quantity_cost_and_reference(self):
        with self.app.app_context():
            product = db.session.get(Product, self.product_id)
            transaction = record_inventory_movement(
                product,
                transaction_type="sale_out",
                quantity_before=5,
                quantity_after=3,
                source_type="sale",
                source_id=42,
                source_reference="Satış #42",
                barcode_values=["TEST-URUN-001-01", "TEST-URUN-001-02"],
            )
            db.session.commit()

            stored = db.session.get(InventoryTransaction, transaction.id)
            self.assertEqual(stored.transaction_code, "SALE-OUT")
            self.assertEqual(stored.quantity_delta, -2)
            self.assertEqual(stored.quantity_before, 5)
            self.assertEqual(stored.quantity_after, 3)
            self.assertEqual(stored.unit_cost, Decimal("125.00"))
            self.assertEqual(stored.total_cost, Decimal("250.00"))
            self.assertEqual(stored.source_reference, "Satış #42")
            self.assertIn("TEST-URUN-001-01", stored.barcode_values)

    def test_zero_delta_does_not_create_a_noise_transaction(self):
        with self.app.app_context():
            product = db.session.get(Product, self.product_id)
            transaction = record_inventory_movement(
                product,
                transaction_type="manual_in",
                quantity_before=5,
                quantity_after=5,
                source_type="product",
            )
            db.session.commit()

            self.assertIsNone(transaction)
            self.assertEqual(InventoryTransaction.query.count(), 0)

    def test_audit_record_is_written_for_an_authenticated_page_request(self):
        self.app.config["AUTH_ENABLED"] = True
        with self.client.session_transaction() as browser_session:
            browser_session["auth_user"] = "admin"
            browser_session["auth_csrf_token"] = "test-csrf"

        response = self.client.get("/products/")

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            log = AuditLog.query.filter_by(endpoint="products.index", action="PAGE_VIEW").one()
            self.assertEqual(log.actor_username, "admin")
            self.assertEqual(log.status_code, 200)
            self.assertEqual(log.details, {"path": "/products/"})

    def test_screen_specific_audit_pause_persists_and_records_its_own_change(self):
        with self.app.app_context():
            set_audit_endpoint_paused("products.index", True, site_id=1)
            db.session.commit()

            setting = db.session.get(SystemSetting, "audit_endpoint_paused:1:products.index")
            event = AuditLog.query.filter_by(action="AUDIT_ENDPOINT_PAUSED").one()
            self.assertEqual(setting.value, "1")
            self.assertIn("products.index", get_paused_audit_endpoints(site_id=1))
            self.assertEqual(
                event.details,
                {"site_id": 1, "endpoint": "products.index", "paused": True},
            )

    def test_screen_specific_audit_preferences_are_isolated_by_site(self):
        with self.app.app_context():
            set_audit_endpoint_paused("products.index", True, site_id=1)
            set_audit_endpoint_paused("reports.daily", True, site_id=2)
            db.session.commit()

            self.assertEqual(get_paused_audit_endpoints(site_id=1), {"products.index"})
            self.assertEqual(get_paused_audit_endpoints(site_id=2), {"reports.daily"})

    def test_paused_screen_does_not_write_normal_navigation_events(self):
        self.app.config["AUTH_ENABLED"] = True
        with self.app.app_context():
            set_audit_endpoint_paused("products.index", True, site_id=1)
            db.session.commit()
        with self.client.session_transaction() as browser_session:
            browser_session["auth_user"] = "admin"
            browser_session["auth_csrf_token"] = "test-csrf"
            browser_session["active_site_id"] = 1
            browser_session["active_store_id"] = 1

        response = self.client.get("/products/")

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(
                AuditLog.query.filter_by(endpoint="products.index", action="PAGE_VIEW").count(),
                0,
            )

    def test_audit_screen_pause_form_requires_csrf_and_persists_selected_screen(self):
        self.app.config["AUTH_ENABLED"] = True
        with self.client.session_transaction() as browser_session:
            browser_session["auth_user"] = "admin"
            browser_session["auth_csrf_token"] = "test-csrf"
            browser_session["active_site_id"] = 1
            browser_session["active_store_id"] = 1

        active_endpoints = [
            endpoint
            for endpoint in AUDITABLE_ENDPOINT_LABELS
            if endpoint in self.app.view_functions and endpoint != "reports.daily"
        ]
        response = self.client.post(
            "/audit-logs/settings/endpoint-audit",
            data={
                "csrf_token": "test-csrf",
                "active_endpoints": active_endpoints,
            },
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIn("reports.daily", get_paused_audit_endpoints(site_id=1))

    def test_legacy_global_pause_value_cannot_disable_screen_level_auditing(self):
        self.app.config["AUTH_ENABLED"] = True
        with self.app.app_context():
            db.session.add(SystemSetting(key="audit_logging_enabled", value="0"))
            db.session.commit()
        with self.client.session_transaction() as browser_session:
            browser_session["auth_user"] = "admin"
            browser_session["auth_csrf_token"] = "test-csrf"

        response = self.client.get("/products/")

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(
                AuditLog.query.filter_by(endpoint="products.index", action="PAGE_VIEW").count(),
                1,
            )

    def test_audit_and_inventory_history_pages_render(self):
        self.app.config["AUTH_ENABLED"] = True
        with self.client.session_transaction() as browser_session:
            browser_session["auth_user"] = "admin"
            browser_session["auth_csrf_token"] = "test-csrf"
        self.client.get("/products/")
        audit_response = self.client.get("/audit-logs/")
        history_response = self.client.get("/inventory-history/")

        self.assertEqual(audit_response.status_code, 200)
        self.assertIn("Sistem Denetim Günlüğü", audit_response.get_data(as_text=True))
        self.assertIn("Ekran Kayıt Seçeneklerini Yönet", audit_response.get_data(as_text=True))
        self.assertIn("Sistem hareketleri", audit_response.get_data(as_text=True))
        self.assertEqual(history_response.status_code, 200)
        self.assertIn("Envanter İşlem Tarihçesi", history_response.get_data(as_text=True))

    def test_failed_login_is_recorded_without_storing_password_data(self):
        self.app.config.update(
            AUTH_ENABLED=True,
            AUTH_USERNAME="admin",
            AUTH_PASSWORD="secret",
            AUTH_PASSWORD_HASH="",
        )
        login_page = self.client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', login_page.get_data(as_text=True)).group(1)

        response = self.client.post(
            "/login",
            data={"username": "admin", "password": "wrong-password", "csrf_token": token},
        )

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            event = AuditLog.query.filter_by(action="LOGIN_FAILED").one()
            self.assertEqual(event.details, {"username": "admin", "reason": "invalid_credentials"})

    def test_logout_is_recorded_before_the_session_is_cleared(self):
        self.app.config["AUTH_ENABLED"] = True
        with self.client.session_transaction() as browser_session:
            browser_session["auth_user"] = "admin"
            browser_session["auth_csrf_token"] = "test-csrf"

        response = self.client.post("/logout", data={"csrf_token": "test-csrf"})

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            event = AuditLog.query.filter_by(action="LOGOUT").one()
            self.assertEqual(event.actor_username, "admin")


if __name__ == "__main__":
    unittest.main()
