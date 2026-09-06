import hashlib
from datetime import datetime, timedelta
from secrets import compare_digest, token_urlsafe
from urllib.parse import urlparse, urljoin

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models import AuthThrottle
from app.services.auth_settings import get_auth_username
from app.services.audit_trail import persist_audit_event
from app.services.identity_access import IdentityScopeError
from app.services.password_policy import password_is_strong
from app.services.two_factor import (
    consume_recovery_code,
    create_enrollment_secret,
    create_recovery_codes,
    decrypt_secret,
    enable_two_factor,
    encrypt_secret,
    provisioning_uri,
    qr_code_data_uri,
    two_factor_required,
    verify_totp,
)
from app.services.user_auth import (
    AuthenticatedIdentity,
    apply_identity_session,
    authenticate_identity,
    database_authentication_active,
    get_current_user,
    inactive_identity_credentials_match,
    mark_login_success,
    update_session_password,
    verify_session_password,
)


bp = Blueprint("auth", __name__)
def get_client_key(username, purpose="password"):
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    ip_address = forwarded_for.split(",", 1)[0].strip() or request.remote_addr or "unknown"
    normalized_username = str(username or "").strip().casefold() or "unknown"
    raw_key = f"{purpose}:{ip_address}:{normalized_username}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_attempt_state(key):
    now = datetime.utcnow()
    record = AuthThrottle.query.filter_by(key_hash=key).with_for_update().one_or_none()
    if record is None:
        return {"record": None, "count": 0, "first": now, "locked_until": None}
    window = current_app.config.get("AUTH_WINDOW_SECONDS", 900)
    if (now - record.first_attempt_at).total_seconds() > window:
        record.attempt_count = 0
        record.first_attempt_at = now
        record.locked_until = None
    return {
        "record": record,
        "count": int(record.attempt_count or 0),
        "first": record.first_attempt_at,
        "locked_until": record.locked_until,
    }


def is_rate_limited(username, purpose="password"):
    state = get_attempt_state(get_client_key(username, purpose))
    return bool(state.get("locked_until") and datetime.utcnow() < state["locked_until"])


def register_failed_attempt(username, purpose="password"):
    key = get_client_key(username, purpose)
    state = get_attempt_state(key)
    record = state.get("record")
    if record is None:
        record = AuthThrottle(key_hash=key, first_attempt_at=state["first"])
        db.session.add(record)
    record.attempt_count = int(state.get("count", 0)) + 1
    if record.attempt_count >= current_app.config.get("AUTH_MAX_ATTEMPTS", 5):
        record.locked_until = datetime.utcnow() + timedelta(
            seconds=current_app.config.get("AUTH_LOCKOUT_SECONDS", 900)
        )


def clear_failed_attempts(username, purpose="password"):
    AuthThrottle.query.filter_by(key_hash=get_client_key(username, purpose)).delete()


def get_csrf_token():
    token = session.get("auth_csrf_token")
    if not token:
        token = token_urlsafe(32)
        session["auth_csrf_token"] = token
    return token


def validate_csrf_token():
    expected = session.get("auth_csrf_token")
    submitted = request.form.get("csrf_token", "")
    return bool(expected) and compare_digest(str(expected), str(submitted))


def is_safe_redirect(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {"http", "https"} and host_url.netloc == redirect_url.netloc


def _resolved_landing_url():
    destination = session.pop("auth_next_url", None) or url_for("dashboard.index")
    if not is_safe_redirect(destination):
        destination = url_for("dashboard.index")
    if destination.rstrip("/") == request.host_url.rstrip("/") or destination == url_for("dashboard.index"):
        from app.services.access_control import first_authorized_landing_url

        destination = first_authorized_landing_url()
    return destination


def _complete_login(identity=None):
    if identity is None:
        user = get_current_user()
        identity = AuthenticatedIdentity(username=user.username, user=user) if user else None
    session["two_factor_verified"] = True
    if identity is not None:
        mark_login_success(identity)
        persist_audit_event(
            "LOGIN_SUCCESS",
            event_type="security",
            entity_type="auth",
            entity_id=identity.username[:80],
            details={"username": identity.username[:120], "two_factor": bool(identity.user)},
        )
    return _resolved_landing_url()


def _pending_login_destination(user):
    if user.must_change_password:
        return url_for("auth.account")
    if two_factor_required():
        if not user.two_factor_enabled:
            return url_for("auth.two_factor_setup")
        if not session.get("two_factor_verified"):
            return url_for("auth.two_factor_verify")
    return _complete_login()


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("dashboard.index")
    if session.get("auth_user"):
        current_user = get_current_user()
        if database_authentication_active() and current_user is not None:
            return redirect(_pending_login_destination(current_user))
        return redirect(next_url if is_safe_redirect(next_url) else url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        next_url = request.form.get("next") or next_url
        if not validate_csrf_token():
            persist_audit_event(
                "LOGIN_REJECTED",
                event_type="security",
                entity_type="auth",
                details={"username": username[:120], "reason": "invalid_csrf"},
            )
            flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        elif is_rate_limited(username):
            persist_audit_event(
                "LOGIN_BLOCKED",
                event_type="security",
                entity_type="auth",
                details={"username": username[:120], "reason": "rate_limited"},
            )
            flash("Çok fazla hatalı deneme yapıldı. Lütfen bir süre sonra tekrar deneyin.", "error")
        else:
            identity = authenticate_identity(username, password)
            if identity is None and inactive_identity_credentials_match(username, password):
                clear_failed_attempts(username)
                persist_audit_event(
                    "LOGIN_REJECTED",
                    event_type="security",
                    entity_type="auth",
                    details={"username": username[:120], "reason": "inactive_user"},
                )
                flash("Kullanıcı hesabınız pasif durumdadır. Sistem yöneticinizle iletişime geçin.", "error")
            elif identity is None:
                register_failed_attempt(username)
                persist_audit_event(
                    "LOGIN_FAILED",
                    event_type="security",
                    entity_type="auth",
                    details={"username": username[:120], "reason": "invalid_credentials"},
                )
                flash("Kullanıcı adı veya şifre hatalı.", "error")
            else:
                clear_failed_attempts(username)
                session.clear()
                try:
                    apply_identity_session(identity)
                    session["auth_csrf_token"] = token_urlsafe(32)
                    session["auth_next_url"] = next_url if is_safe_redirect(next_url) else url_for("dashboard.index")
                    session["two_factor_verified"] = False
                    session.permanent = True
                    if identity.user is not None and identity.user.must_change_password:
                        flash("Devam etmek için geçici şifrenizi değiştirin.", "info")
                        return redirect(url_for("auth.account"))
                    if identity.user is not None and two_factor_required():
                        return redirect(
                            url_for("auth.two_factor_verify")
                            if identity.user.two_factor_enabled
                            else url_for("auth.two_factor_setup")
                        )
                    return redirect(_complete_login(identity))
                except IdentityScopeError as exc:
                    session.clear()
                    persist_audit_event(
                        "LOGIN_REJECTED",
                        event_type="security",
                        entity_type="auth",
                        details={"username": username[:120], "reason": "invalid_operational_scope"},
                    )
                    flash(str(exc), "error")

    return render_template("auth/login.html", next_url=next_url if is_safe_redirect(next_url) else "", csrf_token=get_csrf_token())


@bp.route("/account", methods=["GET", "POST"])
def account():
    username = session.get("auth_user") or get_auth_username()

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not validate_csrf_token():
            persist_audit_event(
                "PASSWORD_CHANGE_REJECTED",
                event_type="security",
                entity_type="auth",
                entity_id=username[:80],
                details={"reason": "invalid_csrf"},
            )
            flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        elif is_rate_limited(username):
            persist_audit_event(
                "PASSWORD_CHANGE_BLOCKED",
                event_type="security",
                entity_type="auth",
                entity_id=username[:80],
                details={"reason": "rate_limited"},
            )
            flash("Çok fazla hatalı deneme yapıldı. Lütfen bir süre sonra tekrar deneyin.", "error")
        elif not verify_session_password(username, current_password):
            register_failed_attempt(username)
            persist_audit_event(
                "PASSWORD_CHANGE_FAILED",
                event_type="security",
                entity_type="auth",
                entity_id=username[:80],
                details={"reason": "invalid_current_password"},
            )
            flash("Mevcut şifre hatalı.", "error")
        elif not password_is_strong(new_password):
            flash("Yeni şifre en az 10 karakter olmalı; büyük harf, küçük harf ve rakam içermeli.", "error")
        elif new_password != confirm_password:
            flash("Yeni şifre tekrarı eşleşmiyor.", "error")
        else:
            clear_failed_attempts(username)
            user = get_current_user()
            was_initial_password = bool(user and user.must_change_password)
            update_session_password(username, new_password)
            persist_audit_event(
                "PASSWORD_CHANGED",
                event_type="security",
                entity_type="auth",
                entity_id=username[:80],
            )
            flash("Şifre güncellendi.", "success")
            if was_initial_password and user is not None and two_factor_required():
                flash("Son adım: Hesabınızı telefonunuzdaki doğrulama uygulamasına bağlayın.", "info")
                return redirect(
                    url_for("auth.two_factor_verify")
                    if user.two_factor_enabled
                    else url_for("auth.two_factor_setup")
                )
            return redirect(url_for("auth.account"))

    return render_template("auth/account.html", username=username, csrf_token=get_csrf_token())


@bp.route("/two-factor/setup", methods=["GET", "POST"])
def two_factor_setup():
    user = get_current_user()
    if user is None or not two_factor_required():
        return redirect(url_for("dashboard.index"))
    if user.must_change_password:
        return redirect(url_for("auth.account"))
    if user.two_factor_enabled:
        return redirect(
            _resolved_landing_url()
            if session.get("two_factor_verified")
            else url_for("auth.two_factor_verify")
        )

    try:
        secret = decrypt_secret(user.two_factor_secret) if user.two_factor_secret else None
    except ValueError:
        secret = None
    if not secret:
        secret = create_enrollment_secret()
        user.two_factor_secret = encrypt_secret(secret)
        user.two_factor_last_counter = None
        db.session.commit()

    if request.method == "POST":
        code = request.form.get("verification_code", "").strip()
        if not validate_csrf_token():
            flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        elif is_rate_limited(user.username, "mfa"):
            flash("Çok fazla hatalı deneme yapıldı. Lütfen bir süre sonra tekrar deneyin.", "error")
        elif not verify_totp(user, code, prevent_replay=False):
            register_failed_attempt(user.username, "mfa")
            persist_audit_event(
                "MFA_ENROLLMENT_FAILED",
                event_type="security",
                entity_type="auth",
                entity_id=str(user.id),
            )
            flash("Kod doğrulanamadı. Telefonda görünen güncel kodu tekrar girin.", "error")
        else:
            clear_failed_attempts(user.username, "mfa")
            recovery_codes = create_recovery_codes()
            enable_two_factor(user, recovery_codes)
            db.session.commit()
            persist_audit_event(
                "MFA_ENROLLED",
                event_type="security",
                entity_type="auth",
                entity_id=str(user.id),
            )
            continue_url = _complete_login()
            return render_template(
                "auth/two_factor_recovery.html",
                recovery_codes=recovery_codes,
                continue_url=continue_url,
            )

    grouped_secret = " ".join(secret[index:index + 4] for index in range(0, len(secret), 4))
    return render_template(
        "auth/two_factor_setup.html",
        csrf_token=get_csrf_token(),
        qr_code=qr_code_data_uri(provisioning_uri(user, secret)),
        manual_key=grouped_secret,
    )


@bp.route("/two-factor/verify", methods=["GET", "POST"])
def two_factor_verify():
    user = get_current_user()
    if user is None or not two_factor_required():
        return redirect(url_for("dashboard.index"))
    if user.must_change_password:
        return redirect(url_for("auth.account"))
    if not user.two_factor_enabled:
        return redirect(url_for("auth.two_factor_setup"))
    if session.get("two_factor_verified"):
        return redirect(_resolved_landing_url())

    if request.method == "POST":
        code = request.form.get("verification_code", "").strip()
        verified = False
        used_recovery_code = False
        if not validate_csrf_token():
            flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        elif is_rate_limited(user.username, "mfa"):
            flash("Çok fazla hatalı deneme yapıldı. Lütfen bir süre sonra tekrar deneyin.", "error")
        else:
            try:
                if code.replace(" ", "").isdigit():
                    verified = verify_totp(user, code)
                else:
                    verified = consume_recovery_code(user, code)
                    used_recovery_code = verified
            except ValueError:
                verified = False
            if verified:
                clear_failed_attempts(user.username, "mfa")
                db.session.commit()
                persist_audit_event(
                    "MFA_VERIFIED",
                    event_type="security",
                    entity_type="auth",
                    entity_id=str(user.id),
                    details={"recovery_code": used_recovery_code},
                )
                if used_recovery_code:
                    flash("Kurtarma koduyla giriş yapıldı. Bu kod artık kullanılamaz.", "info")
                return redirect(_complete_login())
            register_failed_attempt(user.username, "mfa")
            persist_audit_event(
                "MFA_VERIFICATION_FAILED",
                event_type="security",
                entity_type="auth",
                entity_id=str(user.id),
            )
            flash("Kod geçersiz veya süresi dolmuş. Güncel kodu tekrar girin.", "error")

    return render_template("auth/two_factor_verify.html", csrf_token=get_csrf_token())


@bp.route("/logout", methods=["POST"])
def logout():
    if not validate_csrf_token():
        flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        return redirect(url_for("dashboard.index"))
    username = session.get("auth_user")
    persist_audit_event(
        "LOGOUT",
        event_type="security",
        entity_type="auth",
        entity_id=str(username)[:80] if username else None,
    )
    session.clear()
    flash("Oturum kapatıldı.", "success")
    return redirect(url_for("auth.login"))
