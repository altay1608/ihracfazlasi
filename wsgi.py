"""Vercel and other WSGI platforms entrypoint."""

import os

from app import create_app
from app.extensions import db


app = create_app()

# Vercel'de yeni baglanan bos PostgreSQL veritabanini ilk istege hazirla.
# create_all idempotenttir; mevcut tablolar ve veriler degistirilmez.
if os.getenv("VERCEL") and os.getenv("DATABASE_URL", "").strip():
    with app.app_context():
        db.create_all()
