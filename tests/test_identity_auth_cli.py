import json
import re
import unittest
from pathlib import Path
from uuid import uuid4

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Package, Product, Role, Site, Store, User, UserSiteRole
from config import BaseConfig


class IdentityAuthCliTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / f"_identity_auth_{uuid4().hex}.db"
        self.auth_path = Path(__file__).resolve().parent / f"_identity_auth_{uuid4().hex}.json"
        self.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path.as_posix()}"
        self.app = create_app("development")
        self.app.config.update(
            TESTING=True,
            AUTH_ENABLED=True,
            AUTH_USERNAME="admin",
            AUTH_PASSWORD="",
            AUTH_PASSWORD_HASH="",
            AUTH_SETTINGS_PATH=str(self.auth_path),
        )
        self.auth_path.write_text(
            json.dumps({"username": "admin", "password_hash": generate_password_hash("Secret12345")}),
            encoding="utf-8",
        )
        with self.app.app_context():
            db.create_all()
            package = Package(code="PRO", name="Pro")
            lfa = Site(code="LFA", name="La Femme Atelier", package=package, is_sandbox=False)
            dev = Site(code="DEV", name="Development Sandbox", package=package, is_sandbox=True)
            lfa_store = Store(code="MERKEZ", name="Merkez Mağaza", site=lfa)
            dev_store = Store(code="TEST", name="Test Mağaza", site=dev)
            lfa_role = Role(code="OWNER_MANAGER", name="Mağaza Yöneticisi / Sahip", site=lfa, is_system_role=True)
            dev_role = Role(code="OWNER_MANAGER", name="Mağaza Yöneticisi / Sahip", site=dev, is_system_role=True)
            db.session.add_all([package, lfa, dev, lfa_store, dev_store, lfa_role, dev_role])
            db.session.commit()
            self.lfa_id = lfa.id
            self.dev_id = dev.id
            self.dev_store_id = dev_store.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.database_path.unlink(missing_ok=True)
        self.auth_path.unlink(missing_ok=True)

    def _csrf_token(self, client, path="/login"):
        response = client.get(path)
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def test_bootstrap_seed_and_database_login_are_dev_only(self):
        runner = self.app.test_cli_runner()
        bootstrap = runner.invoke(args=["identity", "bootstrap-platform-admin"])
        self.assertEqual(bootstrap.exit_code, 0, bootstrap.output)
        self.assertIn("PLATFORM_ADMIN_HAZIR", bootstrap.output)

        first_seed = runner.invoke(args=["identity", "seed-dev-sandbox"])
        second_seed = runner.invoke(args=["identity", "seed-dev-sandbox"])
        self.assertEqual(first_seed.exit_code, 0, first_seed.output)
        self.assertEqual(second_seed.exit_code, 0, second_seed.output)

        with self.app.app_context():
            user = User.query.filter_by(username="admin").one()
            self.assertTrue(user.is_platform_superadmin)
            memberships = UserSiteRole.query.filter_by(user_id=user.id).all()
            self.assertEqual(len(memberships), 1)
            self.assertEqual(memberships[0].site_id, self.dev_id)
            self.assertTrue(memberships[0].all_stores)
            self.assertEqual(Product.query.filter_by(site_id=self.dev_id).count(), 3)
            self.assertEqual(Product.query.filter_by(site_id=self.lfa_id).count(), 0)
            db.session.add(Store(site_id=self.dev_id, code="AAA", name="Boş Test Mağazası"))
            db.session.commit()

        client = self.app.test_client()
        response = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "Secret12345",
                "csrf_token": self._csrf_token(client),
                "next": "/",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with client.session_transaction() as browser_session:
            self.assertEqual(browser_session["active_site_id"], self.dev_id)
            self.assertEqual(browser_session["active_store_id"], self.dev_store_id)
            self.assertIn("auth_user_id", browser_session)

        dashboard = client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        products_page = client.get("/products/")
        self.assertEqual(products_page.status_code, 200)
        products_html = products_page.get_data(as_text=True)
        self.assertIn("Demo Erkek Gömlek Beyaz", products_html)
        self.assertIn("DEV - Boş Test Mağazası &amp; Test Mağaza", products_html)
        barcode_lookup = client.get("/products/barcode/990000000001-01")
        self.assertEqual(barcode_lookup.status_code, 200, barcode_lookup.get_data(as_text=True))
        self.assertEqual(barcode_lookup.get_json()["product"]["product_code"], "DEV000001")
        self.assertEqual(client.get("/products/barcode/990000000001").status_code, 404)
        self.assertEqual(client.get("/products/barcode/99000000000101").status_code, 404)

    def test_bootstrap_invalidates_existing_legacy_session(self):
        client = self.app.test_client()
        legacy_login = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "Secret12345",
                "csrf_token": self._csrf_token(client),
                "next": "/",
            },
            follow_redirects=False,
        )
        self.assertEqual(legacy_login.status_code, 302)
        with client.session_transaction() as browser_session:
            self.assertNotIn("auth_user_id", browser_session)

        bootstrap = self.app.test_cli_runner().invoke(args=["identity", "bootstrap-platform-admin"])
        self.assertEqual(bootstrap.exit_code, 0, bootstrap.output)

        protected = client.get("/", follow_redirects=False)
        self.assertEqual(protected.status_code, 302)
        self.assertIn("/login", protected.headers["Location"])


if __name__ == "__main__":
    unittest.main()
