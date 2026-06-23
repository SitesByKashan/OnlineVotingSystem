from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 140_000)
    return f"{salt}${base64.b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, saved_digest = password_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 140_000)
    modern = base64.b64encode(digest).decode()
    if hmac.compare_digest(modern, saved_digest):
        return True
    legacy_digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return hmac.compare_digest(base64.b64encode(legacy_digest).decode(), saved_digest)


def hash_otp(code: str) -> str:
    return hmac.new(get_settings().app_secret.encode(), code.encode(), hashlib.sha256).hexdigest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode())


def create_access_token(subject: int, role: str, expires_minutes: int | None = None) -> tuple[str, str, datetime]:
    settings = get_settings()
    expires_at = utc_now() + timedelta(minutes=expires_minutes or settings.access_token_minutes)
    jti = secrets.token_urlsafe(18)
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "jti": jti,
        "iat": int(time.time()),
        "exp": int(expires_at.timestamp()),
    }
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}.{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(settings.app_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}", jti, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected = _b64url(hmac.new(get_settings().app_secret.encode(), signing_input.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature_part, expected):
            raise ValueError
        payload = json.loads(_b64url_decode(payload_part).decode())
    except (ValueError, json.JSONDecodeError):
        raise credentials_error from None
    if int(payload.get("exp", 0)) < int(time.time()):
        raise credentials_error
    return payload
