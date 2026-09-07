from dataclasses import dataclass
import os

from flask import has_request_context, session
from sqlalchemy import func, inspect
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Site, Store, User
from app.services.auth_settings import update_auth_password, verify_credentials
from app.services.identity_access import IdentityScopeError, eligible_operational_memberships
from app.utils import now_in_istanbul


@dataclass(frozen=True)
class AuthenticatedIdentity:
    username: str
    user: User | None = None

    @property
    def uses_database(self):
        return self.user is not None


def _users_table_exists():
    try:
        return inspect(db.engine).has_table("users")
    except SQLAlchemyError:
        db.session.rollback()
        return False


def _database_has_users():
    if not _users_table_exists():
        return False
    try:
        return db.session.query(User.id).limit(1).first() is not None
    except SQLAlchemyError:
        db.session.rollback()
        return False


def database_authentication_active():
    return _database_has_users()


def authenticate_identity(username, password):
    normalized_username = str(username or "").strip()
    if _database_has_users():
        user = User.query.filter(func.lower(User.username) == normalized_username.casefold()).first()
        if not user or not user.is_active:
            return None
        if not check_password_hash(user.password_hash, str(password or "")):
            return None
        return AuthenticatedIdentity(username=user.username, user=user)

    if verify_credentials(normalized_username, password):
        return AuthenticatedIdentity(username=normalized_username)
    return None


def inactive_identity_credentials_match(username, password):
    """Return true only when a known inactive database user supplied the right password."""
    if not _database_has_users():
        return False
    normalized_username = str(username or "").strip().casefold()
    user = User.query.filter(func.lower(User.username) == normalized_username).first()
    return bool(
        user
        and not user.is_active
        and check_password_hash(user.password_hash, str(password or ""))
    )


def _select_store(user, membership):
    if membership.all_stores:
        if membership.site.is_sandbox:
            sandbox_store = (
                Store.query.filter_by(
                    site_id=membership.site_id,
                    code="TEST",
                    is_active=True,
                )
                .order_by(Store.id.asc())
                .first()
            )
            if sandbox_store is not None:
                return sandbox_store
        return (
            Store.query.filter_by(site_id=membership.site_id, is_active=True)
            .order_by(Store.code.asc(), Store.id.asc())
            .first()
        )

    allowed_store_ids = {
        access.store_id
        for access in user.store_access
        if access.store is not None
        and access.store.site_id == membership.site_id
        and access.store.is_active
    }
    if not allowed_store_ids:
        return None
    return (
        Store.query.filter(Store.id.in_(allowed_store_ids), Store.is_active.is_(True))
        .order_by(Store.code.asc(), Store.id.asc())
        .first()
    )


def apply_identity_session(identity):
    session["auth_user"] = identity.username
    if not identity.uses_database:
        site_code = (os.getenv("CUSTOMER_SITE_CODE") or "IFG").strip().upper()
        store_code = (os.getenv("CUSTOMER_STORE_CODE") or "MERKEZ").strip().upper()
        site = Site.query.filter_by(code=site_code, is_active=True).first()
        if site is not None:
            store = Store.query.filter_by(
                site_id=site.id,
                code=store_code,
                is_active=True,
            ).first()
            if store is not None:
                session["active_site_id"] = site.id
                session["active_store_id"] = store.id
                session["active_site_code"] = site.code
                session["active_store_code"] = store.code
        return

    user = identity.user
    memberships = sorted(
        eligible_operational_memberships(user),
        key=lambda item: (item.site.code, item.site_id),
    )
    if not memberships:
        raise IdentityScopeError("Kullanıcıya atanmış aktif ve kullanılabilir bir site bulunamadı.")

    membership = memberships[0]
    store = _select_store(user, membership)
    if store is None:
        raise IdentityScopeError("Kullanıcıya atanmış aktif ve kullanılabilir bir mağaza bulunamadı.")

    session["auth_user_id"] = user.id
    session["active_site_id"] = membership.site_id
    session["active_store_id"] = store.id
    session["active_role_id"] = membership.role_id
    session["active_site_code"] = membership.site.code
    session["active_store_code"] = store.code
    session["site_session_revision"] = int(membership.site.session_revision or 1)


def get_current_user():
    if not has_request_context():
        return None
    user_id = session.get("auth_user_id")
    if not user_id or not _users_table_exists():
        return None
    try:
        user = db.session.get(User, int(user_id))
    except (SQLAlchemyError, TypeError, ValueError):
        db.session.rollback()
        return None
    return user if user and user.is_active else None


def session_scope_is_valid(user):
    if user is None or not has_request_context():
        return False
    try:
        active_site_id = int(session.get("active_site_id"))
        active_store_id = int(session.get("active_store_id"))
    except (TypeError, ValueError):
        return False

    membership = next(
        (
            item
            for item in eligible_operational_memberships(user)
            if item.site_id == active_site_id and item.role_id == session.get("active_role_id")
        ),
        None,
    )
    if membership is None:
        return False

    site = db.session.get(Site, active_site_id)
    if site is None or int(session.get("site_session_revision") or 0) != int(site.session_revision or 1):
        return False

    store = db.session.get(Store, active_store_id)
    if store is None or not store.is_active or store.site_id != active_site_id:
        return False
    if membership.all_stores:
        return True
    return any(access.store_id == active_store_id for access in user.store_access)


def mark_login_success(identity):
    if not identity.uses_database:
        return
    identity.user.last_login_at = now_in_istanbul()
    db.session.commit()


def verify_session_password(username, password):
    user = get_current_user()
    if user is not None:
        return check_password_hash(user.password_hash, str(password or ""))
    return verify_credentials(username, password)


def update_session_password(username, password):
    user = get_current_user()
    if user is not None:
        user.password_hash = generate_password_hash(str(password or ""))
        user.must_change_password = False
        user.password_changed_at = now_in_istanbul()
        db.session.commit()
        return
    update_auth_password(username, password)
