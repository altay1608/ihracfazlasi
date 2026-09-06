"""Package and role based authorization for UI and direct requests."""

from functools import wraps

from flask import abort, g, has_request_context, jsonify, request, session, url_for

from app.extensions import db
from app.models import Permission, Site, Store
from app.services.user_auth import database_authentication_active, get_current_user


BLUEPRINT_ACCESS = {
    "dashboard": "dashboard.access",
    "products": "products.access",
    "inventory_history": "inventory_history.access",
    "sales": "sales.access",
    "reports": None,
    "returns": "returns.access",
    "alerts": "alerts.access",
    "inventory_counts": "inventory_counts.access",
    "admin": "reference_data.access",
    "audit": "audit.access",
}


ENDPOINT_PERMISSIONS = {
    "reports.daily": "daily_reports.access",
    "reports.profit": "profit_reports.access",
    "reports.profit_export": "profit_reports.action.export",
    "products.add": "products.action.create",
    "products.edit": "products.action.edit",
    "products.delete": "products.action.delete",
    "products.bulk_delete": "products.action.delete",
    "products.bulk_labels": "products.action.label",
    "products.label": "products.action.label",
    "products.bulk_multiplier": "products.action.multiplier",
    "products.update_stock": "products.action.stock",
    "products.download_template": "products.action.import",
    "products.upload_template": "products.action.import",
    "products.get_by_barcode": "sales.action.complete",
    "sales.complete": "sales.action.complete",
    "sales.edit": "sales.action.edit",
    "sales.update": "sales.action.edit",
    "sales.receipt": "sales.action.receipt",
    "sales.customer_search": "sales.customer.view",
    "sales.customer_recent": "sales.customer.view",
    "returns.create": "returns.action.create",
    "returns.receipt": "returns.action.receipt",
    "alerts.update_category_threshold": "alerts.action.manage",
    "alerts.update_product_threshold": "alerts.action.manage",
    "inventory_counts.create": "inventory_counts.action.create",
    "inventory_counts.scan": "inventory_counts.action.scan",
    "inventory_counts.remove_scan": "inventory_counts.action.scan",
    "inventory_counts.save": "inventory_counts.action.save",
    "inventory_counts.approve": "inventory_counts.action.approve",
    "inventory_counts.delete": "inventory_counts.action.delete",
    "admin.create": "reference_data.action.manage",
    "admin.edit": "reference_data.action.manage",
    "admin.delete": "reference_data.action.manage",
    "admin.toggle_record": "reference_data.action.manage",
    "admin.toggle_payment_method": "reference_data.action.manage",
    "audit.update_endpoint_audit": "audit.action.manage",
}


LANDING_PAGES = (
    ("dashboard.access", "dashboard.index"),
    ("products.access", "products.index"),
    ("inventory_history.access", "inventory_history.index"),
    ("sales.access", "sales.index"),
    ("daily_reports.access", "reports.daily"),
    ("profit_reports.access", "reports.profit"),
    ("returns.access", "returns.index"),
    ("alerts.access", "alerts.index"),
    ("inventory_counts.access", "inventory_counts.index"),
    ("reference_data.access", "admin.index"),
    ("audit.access", "audit.index"),
    ("finance.access", "finance.index"),
)


def _active_membership(user):
    if user is None:
        return None
    try:
        site_id = int(session.get("active_site_id"))
        role_id = int(session.get("active_role_id"))
    except (TypeError, ValueError):
        return None
    return next(
        (
            membership
            for membership in user.memberships
            if membership.is_active
            and membership.site_id == site_id
            and membership.role_id == role_id
            and membership.role is not None
            and membership.role.is_active
        ),
        None,
    )


def effective_permission_codes(user=None):
    if not database_authentication_active():
        return frozenset()

    user = user or get_current_user()
    membership = _active_membership(user)
    if membership is None:
        return frozenset()

    package = membership.site.package
    package_features = {feature.code for feature in package.features} if package is not None else set()
    allowed = {
        permission.code
        for permission in membership.role.permissions
        if permission.feature is not None and permission.feature.code in package_features
    }
    if user.is_platform_superadmin and membership.site.is_sandbox:
        allowed.update(
            permission.code
            for permission in Permission.query.all()
            if permission.code.startswith("platform.")
        )
    return frozenset(allowed)


def has_permission(code, user=None):
    if not code:
        return True
    if not has_request_context():
        return False
    if not database_authentication_active():
        return True
    resolved_user = user or get_current_user()
    membership = _active_membership(resolved_user)
    if (
        resolved_user is not None
        and resolved_user.is_platform_superadmin
        and membership is not None
        and membership.site.is_sandbox
    ):
        return True
    cache = getattr(g, "effective_permission_codes", None)
    if cache is None or user is not None:
        cache = effective_permission_codes(user=resolved_user)
        if user is None:
            g.effective_permission_codes = cache
    return code in cache


def _deny_access():
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": False, "message": "Bu işlem için yetkiniz bulunmuyor."}), 403
    abort(403)


def permission_required(code):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not has_permission(code):
                return _deny_access()
            return view(*args, **kwargs)

        return wrapped

    return decorator


def platform_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None or not user.is_platform_superadmin:
            return _deny_access()
        return view(*args, **kwargs)

    return wrapped


def first_authorized_landing_url():
    for permission_code, endpoint in LANDING_PAGES:
        if has_permission(permission_code):
            return url_for(endpoint)
    return url_for("auth.account")


def required_permission_for_request():
    endpoint = request.endpoint or ""
    if endpoint in ENDPOINT_PERMISSIONS:
        return ENDPOINT_PERMISSIONS[endpoint]
    return BLUEPRINT_ACCESS.get(request.blueprint)


def register_permission_guard(app):
    @app.before_request
    def enforce_permissions():
        if request.endpoint in {None, "static", "service_worker"} or request.blueprint == "auth":
            return None
        if not session.get("auth_user"):
            return None
        required = required_permission_for_request()
        if required and not has_permission(required):
            return _deny_access()
        return None

    @app.context_processor
    def permission_context():
        current_user = get_current_user()
        active_site = None
        active_store = None
        active_location_label = None
        active_location_title = None
        if current_user is not None:
            try:
                active_site = db.session.get(Site, int(session.get("active_site_id")))
                active_store = db.session.get(Store, int(session.get("active_store_id")))
            except (TypeError, ValueError):
                active_site = None
                active_store = None

        if active_site is not None and active_store is not None:
            membership = _active_membership(current_user)
            store_names = [active_store.name]
            if membership is not None and membership.all_stores:
                accessible_stores = (
                    Store.query.filter_by(site_id=active_site.id, is_active=True)
                    .order_by(Store.name.asc(), Store.id.asc())
                    .all()
                )
                store_names = [store.name for store in accessible_stores]
            active_location_label = (
                f"{active_site.code} - {' & '.join(store_names)}"
                if len(store_names) > 1
                else f"{active_site.code} · {active_store.name}"
            )
            active_location_title = (
                f"Aktif mağaza: {active_store.name} | Erişim: {' & '.join(store_names)}"
            )
        return {
            "can": has_permission,
            "is_platform_superadmin": bool(current_user and current_user.is_platform_superadmin),
            "active_site": active_site,
            "active_store": active_store,
            "active_location_label": active_location_label,
            "active_location_title": active_location_title,
        }
