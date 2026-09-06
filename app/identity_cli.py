from decimal import Decimal
import os

import click
from flask import current_app
from flask.cli import AppGroup
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    Category,
    PaymentMethod,
    Product,
    ProductBarcode,
    RetailMultiplier,
    ReturnReason,
    Role,
    Site,
    Store,
    StoreInventory,
    User,
    UserSiteRole,
    Variant,
)
from app.services.auth_settings import get_auth_password_hash, get_auth_username
from app.services.identity_access import validate_membership_scope


identity_cli = AppGroup("identity", help="Site, kullanıcı ve DEV sandbox yönetimi.")


def _require_dev_scope():
    site = Site.query.filter_by(code="DEV", is_sandbox=True, is_active=True).first()
    if site is None:
        raise click.ClickException("Aktif DEV sandbox sitesi bulunamadı; önce migration çalıştırılmalıdır.")
    store = Store.query.filter_by(site_id=site.id, code="TEST", is_active=True).first()
    role = Role.query.filter_by(site_id=site.id, code="OWNER_MANAGER", is_active=True).first()
    if store is None or role is None:
        raise click.ClickException("DEV sitesi için Test Mağaza veya yönetici rolü bulunamadı.")
    return site, store, role


@identity_cli.command("bootstrap-platform-admin")
def bootstrap_platform_admin():
    """Move the existing legacy admin identity into the DEV sandbox."""
    site, _store, role = _require_dev_scope()
    username = get_auth_username()
    user = User.query.filter_by(username=username).first()

    if user is None:
        password_hash = get_auth_password_hash()
        if not password_hash:
            legacy_password = str(current_app.config.get("AUTH_PASSWORD") or "")
            if not legacy_password:
                raise click.ClickException("Taşınabilecek mevcut parola veya parola özeti bulunamadı.")
            password_hash = generate_password_hash(legacy_password)
        user = User(
            username=username,
            full_name="Platform Administrator",
            password_hash=password_hash,
            must_change_password=False,
            is_platform_superadmin=True,
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.is_platform_superadmin = True
        user.is_active = True
        user.must_change_password = False

    customer_memberships = [membership for membership in user.memberships if not membership.site.is_sandbox]
    if customer_memberships:
        raise click.ClickException("Platform admin üzerinde müşteri sitesi üyeliği bulundu; işlem güvenlik nedeniyle durduruldu.")

    validate_membership_scope(user, site)
    membership = UserSiteRole.query.filter_by(user_id=user.id, site_id=site.id).first()
    if membership is None:
        membership = UserSiteRole(
            user=user,
            site=site,
            role=role,
            all_stores=True,
            is_active=True,
        )
        db.session.add(membership)
    else:
        membership.role = role
        membership.all_stores = True
        membership.is_active = True

    db.session.commit()
    click.echo(f"PLATFORM_ADMIN_HAZIR username={user.username} site=DEV store=TEST")


@identity_cli.command("bootstrap-customer-owner")
def bootstrap_customer_owner():
    """Create the dedicated store owner account for the customer site."""
    site_code = os.getenv("CUSTOMER_SITE_CODE", "IFG").strip().upper()
    store_code = os.getenv("CUSTOMER_STORE_CODE", "MERKEZ").strip().upper()
    site = Site.query.filter_by(code=site_code, is_sandbox=False, is_active=True).first()
    if site is None:
        raise click.ClickException(f"Aktif müşteri sitesi bulunamadı: {site_code}")

    store = Store.query.filter_by(site_id=site.id, code=store_code, is_active=True).first()
    role = Role.query.filter_by(site_id=site.id, code="OWNER_MANAGER", is_active=True).first()
    if store is None or role is None:
        raise click.ClickException("Müşteri mağazası veya mağaza yöneticisi rolü bulunamadı.")

    username = get_auth_username()
    user = User.query.filter_by(username=username).first()
    if user is None:
        password_hash = get_auth_password_hash()
        if not password_hash:
            password = str(current_app.config.get("AUTH_PASSWORD") or "")
            if not password:
                raise click.ClickException("AUTH_PASSWORD veya AUTH_PASSWORD_HASH zorunludur.")
            password_hash = generate_password_hash(password)
        user = User(
            username=username,
            full_name="Mağaza Yöneticisi",
            password_hash=password_hash,
            must_change_password=True,
            is_platform_superadmin=False,
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.full_name = user.full_name or "Mağaza Yöneticisi"
        user.is_platform_superadmin = False
        user.is_active = True

    UserSiteRole.query.filter(
        UserSiteRole.user_id == user.id,
        UserSiteRole.site_id != site.id,
    ).delete(synchronize_session=False)
    membership = UserSiteRole.query.filter_by(user_id=user.id, site_id=site.id).first()
    if membership is None:
        membership = UserSiteRole(user=user, site=site, role=role, all_stores=True, is_active=True)
        db.session.add(membership)
    else:
        membership.role = role
        membership.all_stores = True
        membership.is_active = True

    db.session.commit()
    click.echo(f"CUSTOMER_OWNER_HAZIR username={user.username} site={site.code} store={store.code}")


def _get_or_create(model, defaults=None, **lookup):
    record = model.query.filter_by(**lookup).first()
    if record is not None:
        return record, False
    record = model(**lookup, **(defaults or {}))
    db.session.add(record)
    db.session.flush()
    return record, True


@identity_cli.command("seed-dev-sandbox")
def seed_dev_sandbox():
    """Create fictive operational data only inside DEV / Test Mağaza."""
    site, store, _role = _require_dev_scope()

    for name in ("Demo Erkek Giyim", "Demo Erkek Aksesuar"):
        _get_or_create(Category, site_id=site.id, name=name, defaults={"is_active": True})
    for name in ("STD", "M"):
        _get_or_create(Variant, site_id=site.id, name=name, defaults={"is_active": True})
    for name in ("Nakit", "Kredi Kartı"):
        _get_or_create(PaymentMethod, site_id=site.id, name=name, defaults={"is_active": True})
    for name in ("Beden Uyumsuzluğu", "Müşteri Tercihi"):
        _get_or_create(ReturnReason, site_id=site.id, name=name, defaults={"is_active": True})

    multiplier, _ = _get_or_create(
        RetailMultiplier,
        site_id=site.id,
        name="Demo Premium 2.25x",
        defaults={"multiplier": Decimal("2.25"), "is_active": True, "is_default": True},
    )
    product_rows = (
        ("DEV000001", "990000000001", "Demo Erkek Gömlek Beyaz", "Demo Erkek Giyim", "M", "600.00", "1350.00", 3),
        ("DEV000002", "990000000002", "Demo Erkek Ceket Lacivert", "Demo Erkek Giyim", "L", "900.00", "2025.00", 2),
        ("DEV000003", "990000000003", "Demo Erkek Kemer Siyah", "Demo Erkek Aksesuar", "STD", "500.00", "1125.00", 4),
    )
    created_products = 0
    for code, barcode, name, category, variant, purchase, sale, quantity in product_rows:
        product, created = _get_or_create(
            Product,
            site_id=site.id,
            product_code=code,
            defaults={
                "barcode": barcode,
                "name": name,
                "category": category,
                "variant": variant,
                "purchase_price": Decimal(purchase),
                "sale_price": Decimal(sale),
                "_legacy_stock_quantity": quantity,
                "critical_stock_level": 1,
                "retail_multiplier_id": multiplier.id,
            },
        )
        created_products += int(created)
        inventory, inventory_created = _get_or_create(
            StoreInventory,
            site_id=site.id,
            store_id=store.id,
            product_id=product.id,
            defaults={"stock_quantity": quantity, "critical_stock_level": 1},
        )
        if inventory_created:
            product._legacy_stock_quantity = quantity
        for sequence_no in range(1, quantity + 1):
            _get_or_create(
                ProductBarcode,
                site_id=site.id,
                store_id=store.id,
                product_id=product.id,
                sequence_no=sequence_no,
                defaults={"barcode": f"{barcode}-{sequence_no:02d}", "status": "available"},
            )

    db.session.commit()
    product_count = Product.query.filter_by(site_id=site.id).count()
    stock_total = (
        db.session.query(db.func.coalesce(db.func.sum(StoreInventory.stock_quantity), 0))
        .filter(StoreInventory.site_id == site.id, StoreInventory.store_id == store.id)
        .scalar()
    )
    click.echo(
        f"DEV_SANDBOX_HAZIR site=DEV store=TEST products={product_count} stock={stock_total} created={created_products}"
    )


def register_identity_cli(app):
    app.cli.add_command(identity_cli)
