"""Idempotent first-run setup for managed deployments."""

import os

from app.extensions import db
from app.models import Package, Site, Store


def ensure_deployment_store():
    """Create the customer site/store required by tenant-scoped records."""
    package = Package.query.filter_by(code="PRO").first()
    if package is None:
        package = Package(
            code="PRO",
            name="Pro",
            description="Tüm mağaza yönetimi özellikleri",
            max_stores=5,
            max_users=20,
            is_active=True,
        )
        db.session.add(package)
        db.session.flush()

    site_code = (os.getenv("CUSTOMER_SITE_CODE") or "IFG").strip().upper()
    site_name = (os.getenv("STORE_NAME") or "İhraç Fazlası Giyim").strip()
    site = Site.query.filter_by(code=site_code).first()
    if site is None:
        site = Site(
            package=package,
            code=site_code,
            name=site_name,
            is_sandbox=False,
            is_active=True,
        )
        db.session.add(site)
        db.session.flush()

    store_code = (os.getenv("CUSTOMER_STORE_CODE") or "MERKEZ").strip().upper()
    store = Store.query.filter_by(site_id=site.id, code=store_code).first()
    if store is None:
        store = Store(
            site=site,
            code=store_code,
            name=(os.getenv("STORE_LOCATION_NAME") or "Merkez Mağaza").strip(),
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

    db.session.commit()
    return site, store
