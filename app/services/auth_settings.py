import json
from pathlib import Path
from secrets import compare_digest

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash


def get_settings_path():
    return Path(current_app.config["AUTH_SETTINGS_PATH"])


def load_auth_settings():
    path = get_settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_auth_settings(settings):
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def get_auth_username():
    settings = load_auth_settings()
    return str(settings.get("username") or current_app.config.get("AUTH_USERNAME") or "admin")


def get_auth_password_hash():
    settings = load_auth_settings()
    return str(settings.get("password_hash") or current_app.config.get("AUTH_PASSWORD_HASH") or "")


def verify_credentials(username, password):
    expected_username = get_auth_username()
    username_ok = compare_digest(str(username or ""), expected_username)
    if not username_ok:
        return False

    password_hash = get_auth_password_hash()
    if password_hash:
        return check_password_hash(password_hash, str(password or ""))

    expected_password = str(current_app.config.get("AUTH_PASSWORD") or "")
    return compare_digest(str(password or ""), expected_password)


def update_auth_password(username, password):
    settings = load_auth_settings()
    settings["username"] = str(username or get_auth_username())
    settings["password_hash"] = generate_password_hash(str(password or ""))
    save_auth_settings(settings)
