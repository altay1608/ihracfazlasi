import os
from pathlib import Path
from datetime import timedelta

# Projenin ana dizinini otomatik bulur
BASE_DIR = Path(__file__).resolve().parent


def normalize_database_url(value):
    """Use SQLAlchemy's psycopg v3 dialect for PostgreSQL connection URLs."""
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOW_STOCK_THRESHOLD = 5
    AUTH_ENABLED = os.getenv("AUTH_ENABLED", "1").lower() not in {"0", "false", "no", "off"}
    AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
    AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "")
    AUTH_PASSWORD_HASH = os.getenv("AUTH_PASSWORD_HASH", "")
    AUTH_MAX_ATTEMPTS = int(os.getenv("AUTH_MAX_ATTEMPTS", "5"))
    AUTH_WINDOW_SECONDS = int(os.getenv("AUTH_WINDOW_SECONDS", "900"))
    AUTH_LOCKOUT_SECONDS = int(os.getenv("AUTH_LOCKOUT_SECONDS", "900"))
    MFA_REQUIRED = os.getenv("MFA_REQUIRED", "0").lower() not in {"0", "false", "no", "off"}
    MFA_ISSUER = os.getenv("MFA_ISSUER", "İhraç Fazlası Giyim")
    MFA_ENCRYPTION_KEY = os.getenv("MFA_ENCRYPTION_KEY", "")
    FINANCE_APPROVAL_LIMIT = os.getenv("FINANCE_APPROVAL_LIMIT", "5000")
    AUDIT_LOGGING_ENABLED = os.getenv("AUDIT_LOGGING_ENABLED", "1").lower() not in {"0", "false", "no", "off"}
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv("SESSION_HOURS", "8")))

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = normalize_database_url(
        os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'lafemme.db'}")
    )
    AUTH_SETTINGS_PATH = os.getenv("AUTH_SETTINGS_PATH", str(BASE_DIR / "instance" / "auth.json"))
    SESSION_COOKIE_SECURE = True


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config = {
    "development": DevelopmentConfig,
    "preprod": ProductionConfig,
    "production": ProductionConfig,
    "default": BaseConfig,
}

