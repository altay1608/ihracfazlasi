import os
import unittest
from unittest.mock import patch

from flask import Flask

from app.init import resolve_config_name, validate_production_security


class AppEnvironmentTests(unittest.TestCase):
    def test_linux_defaults_to_production(self):
        with patch.dict(os.environ, {}, clear=True), patch("app.init.platform.system", return_value="Linux"):
            self.assertEqual(resolve_config_name(), "production")

    def test_app_env_must_be_known(self):
        with patch.dict(os.environ, {"APP_ENV": "unexpected"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "APP_ENV"):
                resolve_config_name()

    def test_production_rejects_default_secret(self):
        app = Flask(__name__)
        app.config.update(
            SECRET_KEY="dev-secret-key-change-me",
            AUTH_ENABLED=False,
            AUTH_SETTINGS_PATH="unused.json",
        )

        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
            validate_production_security(app, "production")

    def test_production_accepts_environment_secret(self):
        app = Flask(__name__)
        app.config.update(
            SECRET_KEY="production-secret-key",
            AUTH_ENABLED=False,
            AUTH_SETTINGS_PATH="unused.json",
        )

        validate_production_security(app, "production")


if __name__ == "__main__":
    unittest.main()
