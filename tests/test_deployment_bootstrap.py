import re
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import Site, Store
from app.services.deployment_bootstrap import ensure_deployment_store
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

        for path in ("/products/", "/sales/pos", "/sales/", "/admin/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)


if __name__ == "__main__":
    unittest.main()
