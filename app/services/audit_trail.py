from __future__ import annotations

from flask import current_app, has_request_context, request, session
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import AuditLog, SystemSetting


AUDIT_ENDPOINT_PAUSE_PREFIX = "audit_endpoint_paused:"
EXCLUDED_ENDPOINTS = {"static", "service_worker", "health"}


def get_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    return forwarded_for.split(",", 1)[0].strip() or request.remote_addr or "unknown"


def is_audit_logging_enabled() -> bool:
    """Keep the emergency configuration switch, but never use a database-wide UI pause."""
    return bool(current_app.config.get("AUDIT_LOGGING_ENABLED", True))


def record_audit_event(
    action: str,
    *,
    event_type: str = "system",
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    details: dict | None = None,
    status_code: int | None = None,
    force: bool = False,
) -> AuditLog | None:
    if not force and not is_audit_logging_enabled():
        return None

    actor_username = session.get("auth_user") if has_request_context() else None
    audit_log = AuditLog(
        site_id=session.get("active_site_id") if has_request_context() else None,
        store_id=session.get("active_store_id") if has_request_context() else None,
        user_id=session.get("auth_user_id") if has_request_context() else None,
        actor_username=actor_username,
        event_type=event_type,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        endpoint=request.endpoint if has_request_context() else None,
        request_method=request.method if has_request_context() else None,
        status_code=status_code,
        ip_address=get_client_ip() if has_request_context() else None,
        details=details,
    )
    db.session.add(audit_log)
    return audit_log


def _active_audit_site_id(site_id: int | None = None) -> int | None:
    if site_id is not None:
        return int(site_id)
    if not has_request_context():
        return None
    try:
        return int(session.get("active_site_id"))
    except (TypeError, ValueError):
        return None


def _site_pause_prefix(site_id: int) -> str:
    return f"{AUDIT_ENDPOINT_PAUSE_PREFIX}{site_id}:"


def get_paused_audit_endpoints(site_id: int | None = None) -> set[str]:
    resolved_site_id = _active_audit_site_id(site_id)
    if resolved_site_id is None:
        return set()
    setting_prefix = _site_pause_prefix(resolved_site_id)
    settings = SystemSetting.query.filter(
        SystemSetting.key.like(f"{setting_prefix}%"),
        SystemSetting.value == "1",
    ).all()
    return {
        setting.key[len(setting_prefix):]
        for setting in settings
        if setting.key[len(setting_prefix):]
    }


def is_audit_endpoint_paused(endpoint: str | None) -> bool:
    return bool(endpoint) and endpoint in get_paused_audit_endpoints()


def set_audit_endpoint_paused(endpoint: str, paused: bool, site_id: int | None = None) -> None:
    endpoint = str(endpoint or "").strip()
    if not endpoint:
        raise ValueError("Ekran bilgisi zorunludur.")
    resolved_site_id = _active_audit_site_id(site_id)
    if resolved_site_id is None:
        raise ValueError("Ekran kayıt tercihi için aktif site bulunamadı.")

    setting_key = f"{_site_pause_prefix(resolved_site_id)}{endpoint}"
    setting = db.session.get(SystemSetting, setting_key)
    if paused:
        if setting is None:
            db.session.add(SystemSetting(key=setting_key, value="1"))
        else:
            setting.value = "1"
    elif setting is not None:
        db.session.delete(setting)

    record_audit_event(
        "AUDIT_ENDPOINT_PAUSED" if paused else "AUDIT_ENDPOINT_RESUMED",
        event_type="security",
        entity_type="AuditEndpoint",
        entity_id=endpoint,
        details={"site_id": resolved_site_id, "endpoint": endpoint, "paused": paused},
        force=True,
    )


def persist_audit_event(action: str, **kwargs) -> bool:
    """Write an audit event without allowing audit storage failures to break the request."""
    try:
        record_audit_event(action, **kwargs)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        return False


def should_log_request() -> bool:
    if not has_request_context() or not session.get("auth_user"):
        return False
    if request.endpoint in EXCLUDED_ENDPOINTS or request.endpoint is None:
        return False
    if is_audit_endpoint_paused(request.endpoint):
        return False
    return request.method in {"GET", "POST", "PUT", "PATCH", "DELETE"}


def record_request_audit(response) -> None:
    try:
        if not should_log_request():
            return
        persist_audit_event(
            "PAGE_VIEW" if request.method == "GET" else f"REQUEST_{request.method}",
            event_type="navigation" if request.method == "GET" else "request",
            details={"path": request.path},
            status_code=response.status_code,
        )
    except SQLAlchemyError:
        db.session.rollback()
