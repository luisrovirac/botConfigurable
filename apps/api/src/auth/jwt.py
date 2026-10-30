from datetime import datetime, timedelta
from typing import Any

import jwt

from core.config import get_settings


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.utcnow()
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=settings.access_token_expire_minutes)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.utcnow()
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(days=settings.refresh_token_expire_days), "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
