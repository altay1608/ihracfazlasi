import re
import unittest
from pathlib import Path
from uuid import uuid4

import pyotp
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Feature, Package, Permission, Role, Site, Store, User, UserSiteRole
from app.services.two_factor import decrypt_secret
from config import BaseConfig


class TwoFactorAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / f"_mfa_{uuid4().hex}.db"
        self.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path.as_posix()}"
        self.app = create_app("development")
        self.app.config.update(
            TESTING=True,
            TEST_MFA_ENABLED=True,
            MFA_REQUIRED=True,
            AUTH_ENABLED=True,
            SECRET_KEY="mfa-test-secret",
        )
        with self.app.app_context():
            db.create_all()
            feature = Feature(code="dashboard", name="Kontrol Merkezi", sort_order=1)
            permission = Permission(
                code="dashboard.access",
                name="Kontrol Merkezi",
                kind="menu",
                feature=feature,
                sort_order=1,
            )
            package = Package(code="PRO", name="Pro", features=[feature])
            site = Site(code="DEV", name="Development Sandbox", package=package, is_sandbox=True)
            store = Store(code="TEST", name="Test Mağaza", site=site)
            role = Role(code="OWNER_MANAGER", name="Mağaza Yöneticisi / Sahip", site=site)
            role.permissions = [permission]
            user = User(
                username="admin",
                full_name="Platform Admin",
                password_hash=generate_password_hash("AdminSecret123"),
                must_change_password=False,
                is_platform_superadmin=True,
            )
            db.session.add_all([feature, permission, package, site, store, role, user])
            db.session.flush()
            db.session.add(
                UserSiteRole(
                    user_id=user.id,
                    site_id=site.id,
                    role_id=role.id,
                    all_stores=True,
                )
            )
            db.session.commit()
            self.user_id = user.id
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.database_path.unlink(missing_ok=True)

    def _csrf(self, path):
        response = self.client.get(path)
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def _login(self):
        return self.client.post(
            "/login",
            data={
                "username": "admin",
                "password": "AdminSecret123",
                "csrf_token": self._csrf("/login"),
                "next": "/",
            },
            follow_redirects=False,
        )

    def _current_totp(self):
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            return pyotp.TOTP(decrypt_secret(user.two_factor_secret)).now()

    def _enroll(self):
        self.assertIn("/two-factor/setup", self._login().headers["Location"])
        token = self._csrf("/two-factor/setup")
        response = self.client.post(
            "/two-factor/setup",
            data={"csrf_token": token, "verification_code": self._current_totp()},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Kurtarma kodlarını saklayın", response.get_data(as_text=True))
        return re.findall(r"<code>([A-F0-9]{6}-[A-F0-9]{6})</code>", response.get_data(as_text=True))

    def test_password_login_is_blocked_until_enrollment_finishes(self):
        response = self._login()
        self.assertEqual(response.status_code, 302)
        self.assertIn("/two-factor/setup", response.headers["Location"])

        blocked = self.client.get("/", follow_redirects=False)
        self.assertEqual(blocked.status_code, 302)
        self.assertIn("/two-factor/setup", blocked.headers["Location"])

        codes = self._enroll_from_existing_session()
        self.assertEqual(len(codes), 8)
        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("DEV · Test Mağaza", dashboard.get_data(as_text=True))

    def _enroll_from_existing_session(self):
        token = self._csrf("/two-factor/setup")
        response = self.client.post(
            "/two-factor/setup",
            data={"csrf_token": token, "verification_code": self._current_totp()},
            follow_redirects=False,
        )
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Kurtarma kodlarını saklayın", html)
        return re.findall(r"<code>([A-F0-9]{6}-[A-F0-9]{6})</code>", html)

    def test_totp_cannot_be_replayed(self):
        self._enroll()
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            totp = pyotp.TOTP(decrypt_secret(user.two_factor_secret))
            replay_code = totp.at(int(user.two_factor_last_counter) * totp.interval)
        with self.client.session_transaction() as login_session:
            login_session.clear()
        self.assertIn("/two-factor/verify", self._login().headers["Location"])
        token = self._csrf("/two-factor/verify")
        response = self.client.post(
            "/two-factor/verify",
            data={"csrf_token": token, "verification_code": replay_code},
            follow_redirects=True,
        )
        self.assertIn("Kod geçersiz veya süresi dolmuş", response.get_data(as_text=True))

    def test_recovery_code_is_single_use(self):
        codes = self._enroll()
        recovery_code = codes[0]
        with self.client.session_transaction() as login_session:
            login_session.clear()
        self._login()
        response = self.client.post(
            "/two-factor/verify",
            data={"csrf_token": self._csrf("/two-factor/verify"), "verification_code": recovery_code},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with self.client.session_transaction() as login_session:
            login_session.clear()
        self._login()
        reused = self.client.post(
            "/two-factor/verify",
            data={"csrf_token": self._csrf("/two-factor/verify"), "verification_code": recovery_code},
            follow_redirects=True,
        )
        self.assertIn("Kod geçersiz veya süresi dolmuş", reused.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
