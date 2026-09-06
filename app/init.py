import os
import platform
from hmac import compare_digest

from flask import Flask, abort, g, jsonify, redirect, request, send_from_directory, session, url_for
from pathlib import Path
from sqlalchemy import text

from config import config
from .extensions import db, migrate, register_template_filters


def resolve_config_name(config_name=None):
    if config_name:
        return config_name
    configured_name = os.getenv("APP_ENV", "").strip().lower()
    if configured_name:
        if configured_name not in config:
            raise RuntimeError("APP_ENV development, preprod veya production olmalidir.")
        return configured_name
    return "development" if platform.system() == "Windows" else "production"


def create_app(config_name=None):
    app = Flask(__name__)
    selected_config = resolve_config_name(config_name)
    app.config.from_object(config.get(selected_config, config["default"]))
    validate_production_security(app, selected_config)

    db.init_app(app)
    migrate.init_app(app, db)
    register_template_filters(app)

    from .services.tenant_scope import register_tenant_scope

    register_tenant_scope()

    register_blueprints(app)
    register_pwa_routes(app)
    register_health_route(app)
    register_auth_guard(app)
    register_request_csrf_guard(app)
    register_permission_guard(app)
    register_security_headers(app)
    register_audit_logging(app)
    register_shell_context(app)
    register_cli_commands(app)

    return app


def register_cli_commands(app):
    from .finance_cli import register_finance_cli
    from .identity_cli import register_identity_cli

    register_finance_cli(app)
    register_identity_cli(app)


def register_blueprints(app):
    from .modules.audit.routes import bp as audit_bp
    from .modules.auth.routes import bp as auth_bp
    from .modules.admin.routes import bp as admin_bp
    from .modules.dashboard.routes import bp as dashboard_bp
    from .modules.inventory_counts.routes import bp as inventory_counts_bp
    from .modules.inventory_history.routes import bp as inventory_history_bp
    from .modules.products.routes import bp as products_bp
    from .modules.platform.routes import bp as platform_bp
    from .modules.sales.routes import bp as sales_bp
    from .modules.reports.routes import bp as reports_bp
    from .modules.returns.routes import bp as returns_bp
    from .modules.alerts.routes import bp as alerts_bp
    from .modules.finance.routes import bp as finance_bp
    from .modules.finance_operations.routes import bp as finance_operations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_counts_bp)
    app.register_blueprint(inventory_history_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(platform_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(returns_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(finance_operations_bp)


def register_pwa_routes(app):
    @app.get("/service-worker.js")
    def service_worker():
        response = send_from_directory(
            app.static_folder,
            "js/service-worker.js",
            mimetype="application/javascript",
        )
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


def register_health_route(app):
    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "database": "ok"})
        except Exception:
            db.session.rollback()
            app.logger.exception("Health check failed")
            return jsonify({"status": "error", "database": "unavailable"}), 503


def validate_production_security(app, selected_config):
    if selected_config != "production":
        return
    secret_key = str(app.config.get("SECRET_KEY") or "")
    if not secret_key or secret_key == "dev-secret-key-change-me":
        raise RuntimeError("Production ortaminda SECRET_KEY mutlaka degistirilmelidir.")
    auth_settings_path = Path(app.config["AUTH_SETTINGS_PATH"])
    has_password_hash = bool(app.config.get("AUTH_PASSWORD_HASH"))
    has_saved_password = auth_settings_path.exists()
    has_configured_password = bool(app.config.get("AUTH_PASSWORD"))
    if app.config.get("AUTH_ENABLED", True) and not has_configured_password and not has_password_hash and not has_saved_password:
        raise RuntimeError("Production ortaminda AUTH_PASSWORD veya AUTH_PASSWORD_HASH mutlaka degistirilmelidir.")


def register_auth_guard(app):
    @app.before_request
    def require_login():
        from .services.user_auth import (
            database_authentication_active,
            get_current_user,
            session_scope_is_valid,
        )

        if not app.config.get("AUTH_ENABLED", True):
            return None
        if request.endpoint in {"auth.login", "health", "service_worker", "static"}:
            return None
        if request.endpoint is None:
            return None
        if session.get("auth_user"):
            if not database_authentication_active():
                return None
            current_user = get_current_user()
            if current_user is not None and session_scope_is_valid(current_user):
                g.current_user = current_user
                if (
                    current_user.must_change_password
                    and request.endpoint not in {"auth.account", "auth.logout"}
                ):
                    return redirect(url_for("auth.account"))
                from .services.two_factor import two_factor_required

                if two_factor_required() and not current_user.must_change_password:
                    if not current_user.two_factor_enabled and request.endpoint not in {
                        "auth.two_factor_setup",
                        "auth.logout",
                    }:
                        return redirect(url_for("auth.two_factor_setup"))
                    if (
                        current_user.two_factor_enabled
                        and not session.get("two_factor_verified")
                        and request.endpoint not in {"auth.two_factor_verify", "auth.logout"}
                    ):
                        return redirect(url_for("auth.two_factor_verify"))
                return None
            session.clear()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "Oturum açmanız gerekiyor."}), 401

        next_url = request.full_path if request.query_string else request.path
        return redirect(url_for("auth.login", next=next_url))


def register_permission_guard(app):
    from .services.access_control import register_permission_guard as register_guard

    register_guard(app)


def register_request_csrf_guard(app):
    """Require the session CSRF token for every authenticated state-changing request."""
    @app.before_request
    def enforce_request_csrf():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        if request.blueprint == "auth" or not session.get("auth_user"):
            return None

        expected = str(session.get("auth_csrf_token") or "")
        submitted = str(request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or "")
        if expected and submitted and compare_digest(expected, submitted):
            return None
        if submitted:
            try:
                from flask_wtf.csrf import validate_csrf
                from wtforms.validators import ValidationError

                validate_csrf(submitted)
                return None
            except ValidationError:
                pass
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "İşlem doğrulaması başarısız. Sayfayı yenileyip tekrar deneyin."}), 400
        abort(400)


def register_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.endpoint and request.endpoint.startswith(("auth.", "audit.")):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def register_audit_logging(app):
    from .services.audit_trail import record_request_audit

    @app.after_request
    def write_audit_log(response):
        record_request_audit(response)
        return response


def register_shell_context(app):
    from .models import Category, InventoryCount, InventoryCountLine, PaymentMethod, Product, Return, ReturnItem, ReturnReason, Sale, SaleItem, Variant

    @app.shell_context_processor
    def shell_context():
        return {
            "Category": Category,
            "InventoryCount": InventoryCount,
            "InventoryCountLine": InventoryCountLine,
            "PaymentMethod": PaymentMethod,
            "db": db,
            "Product": Product,
            "Sale": Sale,
            "SaleItem": SaleItem,
            "Return": Return,
            "ReturnItem": ReturnItem,
            "ReturnReason": ReturnReason,
            "Variant": Variant,
        }
