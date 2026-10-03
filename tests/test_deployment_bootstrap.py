import re
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import Product, Site, Store, SystemSetting
from app.services.deployment_bootstrap import DEPLOYMENT_READY_VERSION, ensure_deployment_ready, ensure_deployment_store
from config import BaseConfig


class DeploymentBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / f"_deployment_{uuid4().hex}.db"
        self.auth_path = Path(__file__).resolve().parent / f"_deployment_auth_{uuid4().hex}.json"
        self.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path.as_posix()}"
        self.app = create_app("development")
        self.app.config.update(
            AUTH_ENABLED=True,
            AUTH_USERNAME="admin",
            AUTH_PASSWORD="secret",
            AUTH_PASSWORD_HASH="",
            AUTH_SETTINGS_PATH=str(self.auth_path),
            TESTING=True,
        )
        self.environment = patch.dict(
            "os.environ",
            {
                "CUSTOMER_SITE_CODE": "IFG",
                "CUSTOMER_STORE_CODE": "MERKEZ",
                "STORE_NAME": "İhraç Fazlası Giyim",
            },
        )
        self.environment.start()
        with self.app.app_context():
            db.create_all()
            ensure_deployment_store()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.environment.stop()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.database_path.unlink(missing_ok=True)
        self.auth_path.unlink(missing_ok=True)

    def login(self):
        page = self.client.get("/login")
        token = re.search(
            r'name="csrf_token" value="([^"]+)"',
            page.get_data(as_text=True),
        ).group(1)
        return self.client.post(
            "/login",
            data={
                "username": "admin",
                "password": "secret",
                "csrf_token": token,
                "next": "/",
            },
        )

    def test_empty_managed_database_is_ready_for_store_pages(self):
        with self.app.app_context():
            self.assertIsNotNone(Site.query.filter_by(code="IFG").first())
            self.assertIsNotNone(Store.query.filter_by(code="MERKEZ").first())

        self.assertEqual(self.login().status_code, 302)
        with self.client.session_transaction() as session:
            self.assertIsNotNone(session.get("active_site_id"))
            self.assertIsNotNone(session.get("active_store_id"))

        for path in (
            "/", "/products/", "/products/add", "/products/template/upload",
            "/sales/pos", "/sales/", "/admin/", "/inventory-history/",
            "/inventory-counts/", "/inventory-counts/create", "/returns/",
            "/alerts/", "/reports/daily", "/reports/profit",
            "/finance/", "/finance/accounts", "/finance/manual",
            "/finance/transfers", "/finance/pos-reconciliations",
            "/finance/current-accounts", "/finance/obligations", "/finance/overheads",
            "/finance/operations/", "/finance/operations/expenses",
            "/finance/operations/personnel", "/finance/operations/supplier-invoices",
            "/finance/operations/approvals", "/finance/operations/daily-closing",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        # A return cannot be started without choosing its original sale.
        response = self.client.get("/returns/create")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/returns/"))

    def test_managed_postgres_bootstrap_contains_split_payment_schema(self):
        bootstrap_source = (
            Path(__file__).resolve().parents[1] / "app/services/deployment_bootstrap.py"
        ).read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE IF NOT EXISTS sale_payments", bootstrap_source)
        self.assertIn("CREATE TABLE IF NOT EXISTS credit_sale_collections", bootstrap_source)
        self.assertIn("ix_sale_payments_sale_id", bootstrap_source)
        self.assertIn("ix_credit_sale_collections_sale_id", bootstrap_source)
        self.assertIn(DEPLOYMENT_READY_VERSION, bootstrap_source)
        self.assertIn("ADD COLUMN IF NOT EXISTS linked_current_entry_id", bootstrap_source)
        self.assertIn("ALTER COLUMN current_entry_id DROP NOT NULL", bootstrap_source)
        self.assertIn("ix_supplier_invoices_linked_current_entry_id", bootstrap_source)

    def test_deployment_upgrade_never_resets_existing_data_without_reset_marker(self):
        with self.app.app_context():
            site = Site.query.filter_by(code="IFG").one()
            product = Product(
                site_id=site.id, name="Korunacak Ürün", category="Tshirt",
                barcode="PRESERVE-1", product_code="PRESERVE-1",
                purchase_price=100, sale_price=200,
            )
            db.session.add(product)
            db.session.add(SystemSetting(key="deployment_ready_20261001_v3", value="completed"))
            db.session.commit()
            product_id = product.id
            with patch("app.services.deployment_bootstrap.reset_customer_delivery_data_once") as reset:
                self.assertTrue(ensure_deployment_ready())
                self.assertFalse(ensure_deployment_ready())
                reset.assert_not_called()
            self.assertEqual(db.session.get(Product, product_id).name, "Korunacak Ürün")
            self.assertEqual(Product.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
