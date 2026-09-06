import unittest
import re
from pathlib import Path
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import AuthThrottle
from config import BaseConfig


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.auth_path = Path(__file__).resolve().parent / "_auth_test_settings.json"
        self.database_path = Path(__file__).resolve().parent / f"_auth_{uuid4().hex}.db"
        self.auth_path.unlink(missing_ok=True)
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
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.auth_path.unlink(missing_ok=True)
        self.database_path.unlink(missing_ok=True)

    def get_csrf_token(self, path="/login"):
        response = self.client.get(path)
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def login(self, password="secret"):
        token = self.get_csrf_token("/login")
        return self.client.post(
            "/login",
            data={"username": "admin", "password": password, "next": "/", "csrf_token": token},
            follow_redirects=False,
        )

    def test_protected_page_redirects_to_login(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_login_lists_store_features_without_package_prices(self):
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Satış ve Stok", html)
        self.assertIn("Kontrol", html)
        self.assertIn("Güvenli Yönetim", html)
        self.assertNotIn("₺2.500", html)
        self.assertNotIn("/ ay", html)
        self.assertIn("Hızlı satış ve barkod işlemleri", html)
        self.assertIn("Ürün ve stok takibi", html)
        self.assertIn("İade ve değişim yönetimi", html)
        self.assertIn("Stok sayım yönetimi", html)
        self.assertIn("Kritik stok uyarıları", html)
        self.assertIn("Günlük ve dönemsel raporlar", html)
        self.assertIn("Rol ve yetki kontrolü", html)
        self.assertIn("İki adımlı doğrulama", html)
        self.assertIn("Sistem işlem günlüğü", html)
        self.assertNotIn("AI asistanı", html)

    def test_login_allows_access_to_protected_page(self):
        response = self.login()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))

        protected = self.client.get("/")
        self.assertEqual(protected.status_code, 200)
        html = protected.get_data(as_text=True)
        self.assertIn("user-menu", html)
        self.assertIn("Kullanıcı Bilgileri", html)

    def test_ajax_request_gets_unauthorized_json(self):
        response = self.client.get("/products/", headers={"X-Requested-With": "XMLHttpRequest"})

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.get_json()["success"])

    def test_authenticated_write_requires_csrf_token(self):
        self.login()
        missing = self.client.post(
            "/alerts/categories/999/threshold",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(missing.status_code, 400)
        self.assertIn("doğrulaması", missing.get_json()["message"])

        token = self.get_csrf_token("/")
        accepted = self.client.post(
            "/alerts/categories/999/threshold",
            headers={"X-CSRF-Token": token, "X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(accepted.status_code, 404)

        flask_form_token = self.get_csrf_token("/products/add")
        signed_accepted = self.client.post(
            "/alerts/categories/999/threshold",
            data={"csrf_token": flask_form_token},
        )
        self.assertEqual(signed_accepted.status_code, 404)

    def test_failed_login_attempt_is_persisted(self):
        response = self.login(password="wrong")
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            throttle = AuthThrottle.query.one()
            self.assertEqual(throttle.attempt_count, 1)

    def test_account_page_updates_password(self):
        self.login()
        token = self.get_csrf_token("/account")

        response = self.client.post(
            "/account",
            data={
                "current_password": "secret",
                "new_password": "NewSecret123",
                "confirm_password": "NewSecret123",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        logout_token = self.get_csrf_token("/account")
        self.client.post("/logout", data={"csrf_token": logout_token})
        old_token = self.get_csrf_token("/login")
        old_login = self.client.post(
            "/login",
            data={"username": "admin", "password": "secret", "next": "/", "csrf_token": old_token},
        )
        self.assertEqual(old_login.status_code, 200)

        new_login = self.login(password="NewSecret123")
        self.assertEqual(new_login.status_code, 302)


if __name__ == "__main__":
    unittest.main()
