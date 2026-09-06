"""Simple TOTP-based two-factor authentication with one-time recovery codes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import secrets
import time

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from app.utils import now_in_istanbul


RECOVERY_CODE_COUNT = 8


def two_factor_required():
    if not current_app.config.get("MFA_REQUIRED", True):
        return False
    if current_app.testing and not current_app.config.get("TEST_MFA_ENABLED", False):
        return False
    return True


def _key_material():
    configured = str(current_app.config.get("MFA_ENCRYPTION_KEY") or "").encode("utf-8")
    if configured:
        try:
            decoded = base64.urlsafe_b64decode(configured)
        except Exception as exc:
            raise RuntimeError("MFA_ENCRYPTION_KEY geçerli bir Fernet anahtarı değil.") from exc
        if len(decoded) != 32:
            raise RuntimeError("MFA_ENCRYPTION_KEY 32 baytlık Fernet anahtarı olmalıdır.")
        return configured
    secret_key = str(current_app.config.get("SECRET_KEY") or "").encode("utf-8")
    return base64.urlsafe_b64encode(hashlib.sha256(b"lafemme-mfa-v1:" + secret_key).digest())


def _fernet():
    return Fernet(_key_material())


def encrypt_secret(secret):
    return _fernet().encrypt(str(secret).encode("ascii")).decode("ascii")


def decrypt_secret(encrypted_secret):
    if not encrypted_secret:
        raise ValueError("İki adımlı doğrulama anahtarı bulunamadı.")
    try:
        return _fernet().decrypt(str(encrypted_secret).encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("İki adımlı doğrulama anahtarı çözülemedi.") from exc


def create_enrollment_secret():
    return pyotp.random_base32()


def provisioning_uri(user, secret):
    issuer = current_app.config.get("MFA_ISSUER", "İhraç Fazlası Giyim")
    return pyotp.TOTP(secret).provisioning_uri(name=user.username, issuer_name=issuer)


def qr_code_data_uri(uri):
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _matching_counter(secret, code, valid_window=1):
    normalized = str(code or "").replace(" ", "").strip()
    if len(normalized) != 6 or not normalized.isdigit():
        return None
    totp = pyotp.TOTP(secret)
    current_counter = int(time.time()) // totp.interval
    for offset in range(-valid_window, valid_window + 1):
        counter = current_counter + offset
        if counter >= 0 and hmac.compare_digest(totp.at(counter * totp.interval), normalized):
            return counter
    return None


def verify_totp(user, code, *, prevent_replay=True):
    secret = decrypt_secret(user.two_factor_secret)
    counter = _matching_counter(secret, code)
    if counter is None:
        return False
    if prevent_replay and user.two_factor_last_counter is not None:
        if counter <= int(user.two_factor_last_counter):
            return False
    user.two_factor_last_counter = counter
    return True


def _recovery_digest(code):
    normalized = str(code or "").replace("-", "").replace(" ", "").upper()
    key = hashlib.sha256(b"lafemme-recovery-v1:" + _key_material()).digest()
    return hmac.new(key, normalized.encode("ascii", errors="ignore"), hashlib.sha256).hexdigest()


def create_recovery_codes():
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        value = secrets.token_hex(6).upper()
        codes.append(f"{value[:6]}-{value[6:]}")
    return codes


def recovery_code_hashes(codes):
    return json.dumps([_recovery_digest(code) for code in codes])


def consume_recovery_code(user, code):
    try:
        stored = json.loads(user.two_factor_recovery_codes or "[]")
    except (TypeError, ValueError):
        return False
    submitted = _recovery_digest(code)
    remaining = []
    matched = False
    for digest in stored:
        if not matched and hmac.compare_digest(str(digest), submitted):
            matched = True
        else:
            remaining.append(digest)
    if matched:
        user.two_factor_recovery_codes = json.dumps(remaining)
    return matched


def enable_two_factor(user, recovery_codes):
    user.two_factor_enabled = True
    user.two_factor_confirmed_at = now_in_istanbul()
    user.two_factor_recovery_codes = recovery_code_hashes(recovery_codes)


def reset_two_factor(user):
    user.two_factor_secret = None
    user.two_factor_enabled = False
    user.two_factor_confirmed_at = None
    user.two_factor_recovery_codes = None
    user.two_factor_last_counter = None

