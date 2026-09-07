"""Vercel and other WSGI platforms entrypoint."""

import os

from app import create_app
from app.extensions import db


app = create_app()

# Vercel'de yeni baglanan bos PostgreSQL veritabanini ilk istege hazirla.
# create_all idempotenttir; mevcut tablolar ve veriler degistirilmez.
database_url_is_configured = any(
    os.getenv(key, "").strip()
    for key in (
        "DATABASE_URL",
        "POSTGRES_URL",
        "STORAGE_URL",
        "DATABASE_URL_UNPOOLED",
        "POSTGRES_URL_NON_POOLING",
    )
)
if os.getenv("VERCEL") and database_url_is_configured:
    with app.app_context():
        db.create_all()
