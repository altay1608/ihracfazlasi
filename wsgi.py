"""Vercel and other WSGI platforms entrypoint."""

import os

from app import create_app


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
        # Normal cold starts take one marker query. Schema/store/reset work only
        # runs after a new deployment setup version or on a brand-new database.
        from app.services.deployment_bootstrap import ensure_deployment_ready

        ensure_deployment_ready()
