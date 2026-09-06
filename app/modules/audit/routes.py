from datetime import datetime, time
from secrets import compare_digest

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from app.extensions import db
from app.models import AuditLog
from app.services.audit_trail import get_paused_audit_endpoints, set_audit_endpoint_paused
from app.services.identity_access import get_active_site_id
from app.services.user_auth import get_current_user


bp = Blueprint("audit", __name__, url_prefix="/audit-logs")


AUDITABLE_ENDPOINT_LABELS = {
    "dashboard.index": "Kontrol Merkezi",
    "products.index": "Ürün ve Stok",
    "inventory_history.index": "Envanter İşlem Tarihçesi",
    "sales.pos": "Hızlı Satış",
    "sales.index": "Satış Sipariş Satırları",
    "reports.daily": "Günlük Hızlı Rapor",
    "reports.profit": "Karlılık Analizi",
    "returns.index": "İade Yönetimi",
    "alerts.index": "Kritik Stok Uyarıları",
    "inventory_counts.index": "Stok Sayım Yönetimi",
    "admin.index": "Temel Veri Yönetim Paneli",
}


def parse_date_filter(value, *, end_of_day=False):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    return datetime.combine(parsed, time.max if end_of_day else time.min)


def valid_csrf_token():
    expected = session.get("auth_csrf_token", "")
    submitted = request.form.get("csrf_token", "")
    return bool(expected) and compare_digest(str(expected), str(submitted))


@bp.route("/")
def index():
    actor = request.args.get("actor", "").strip()
    action = request.args.get("action", "").strip()
    search = request.args.get("search", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    query = AuditLog.query
    current_user = get_current_user()
    if current_user is None or not current_user.is_platform_superadmin:
        query = query.filter(AuditLog.site_id == get_active_site_id())
    if actor:
        query = query.filter(AuditLog.actor_username.ilike(f"%{actor}%"))
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.endpoint.ilike(like),
                AuditLog.entity_type.ilike(like),
                AuditLog.entity_id.ilike(like),
            )
        )
    start_at = parse_date_filter(start_date)
    end_at = parse_date_filter(end_date, end_of_day=True)
    if start_at:
        query = query.filter(AuditLog.occurred_at >= start_at)
    if end_at:
        query = query.filter(AuditLog.occurred_at <= end_at)

    logs = query.order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc()).limit(1000).all()
    return render_template(
        "audit/index.html",
        logs=logs,
        endpoint_options=get_audit_endpoint_options(logs),
        paused_endpoints=sorted(get_paused_audit_endpoints()),
        endpoint_labels=AUDITABLE_ENDPOINT_LABELS,
        filters={
            "actor": actor,
            "action": action,
            "search": search,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def get_audit_endpoint_options(logs):
    endpoints = {
        log.endpoint
        for log in logs
        if log.endpoint and log.endpoint in AUDITABLE_ENDPOINT_LABELS
    }
    endpoints.update(
        endpoint
        for endpoint in current_app.view_functions
        if endpoint in AUDITABLE_ENDPOINT_LABELS
    )
    return [
        {"value": endpoint, "label": AUDITABLE_ENDPOINT_LABELS.get(endpoint, endpoint)}
        for endpoint in sorted(endpoints, key=lambda item: AUDITABLE_ENDPOINT_LABELS.get(item, item))
    ]


@bp.route("/settings/endpoint-audit", methods=["POST"])
def update_endpoint_audit():
    if not valid_csrf_token():
        flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        return redirect(url_for("audit.index"))

    active_endpoints = set(request.form.getlist("active_endpoints"))
    allowed_endpoints = set(AUDITABLE_ENDPOINT_LABELS).intersection(current_app.view_functions)
    invalid_endpoints = active_endpoints.difference(allowed_endpoints)
    if invalid_endpoints:
        flash("Geçersiz ekran seçimi algılandı.", "error")
        return redirect(url_for("audit.index"))

    currently_paused = get_paused_audit_endpoints()
    changed_endpoints = []
    for endpoint in sorted(allowed_endpoints):
        should_pause = endpoint not in active_endpoints
        if should_pause == (endpoint in currently_paused):
            continue
        set_audit_endpoint_paused(endpoint, should_pause)
        changed_endpoints.append(endpoint)

    db.session.commit()
    if changed_endpoints:
        flash(f"{len(changed_endpoints)} ekranın kayıt tercihi güncellendi.", "success")
    else:
        flash("Ekran kayıt tercihlerinde değişiklik yok.", "info")
    return redirect(url_for("audit.index"))
