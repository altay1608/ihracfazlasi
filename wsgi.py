"""Vercel and other WSGI platforms entrypoint."""

import os

from app import create_app
from app.extensions import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


app = create_app()

# Vercel PostgreSQL veritabanini ilk istege hazirla ve teslim sifirlamasini
# site bazinda, tek seferlik bir islem olarak uygula.
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
        # Cold start'ta bütün tablo metadatasını yeniden taramak yerine,
        # kurulumun mevcut olup olmadığını tek hızlı sorguyla kontrol et.
        try:
            db.session.execute(text("SELECT 1 FROM system_settings LIMIT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            db.create_all()
        from app.services.deployment_bootstrap import (
            ensure_automatic_pos_schema,
            ensure_deployment_store,
            reset_customer_delivery_data_once,
        )

        ensure_automatic_pos_schema()
        customer_site, _customer_store = ensure_deployment_store()
        reset_customer_delivery_data_once(customer_site.id)
