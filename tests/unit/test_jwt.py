from datetime import timedelta

import pytest

from auth.jwt import InvalidTokenError, TokenService

KEY = "k" * 32  # HS256 recomienda claves de al menos 32 bytes
OTHER_KEY = "o" * 32


def _service(access_ttl: timedelta = timedelta(minutes=15)) -> TokenService:
    return TokenService(
        secret_key=KEY,
        algorithm="HS256",
        access_ttl=access_ttl,
        refresh_ttl=timedelta(days=7),
    )


def test_access_token_roundtrip_keeps_claims() -> None:
    service = _service()
    token = service.create("access", "user-1", {"tenant_id": "tenant-a", "role": "admin"})

    claims = service.decode(token, "access")

    assert claims["sub"] == "user-1"
    assert claims["tenant_id"] == "tenant-a"
    assert claims["type"] == "access"


def test_refresh_token_is_rejected_as_access_token() -> None:
    service = _service()
    refresh = service.create("refresh", "user-1")

    with pytest.raises(InvalidTokenError):
        service.decode(refresh, "access")


def test_claims_cannot_override_token_type() -> None:
    service = _service()
    token = service.create("refresh", "user-1", {"type": "access"})

    with pytest.raises(InvalidTokenError):
        service.decode(token, "access")


def test_expired_token_is_rejected() -> None:
    service = _service(access_ttl=timedelta(seconds=-1))
    token = service.create("access", "user-1")

    with pytest.raises(InvalidTokenError):
        service.decode(token, "access")


def test_token_signed_with_other_key_is_rejected() -> None:
    token = TokenService(OTHER_KEY, "HS256", timedelta(minutes=1), timedelta(days=1)).create(
        "access", "user-1"
    )

    with pytest.raises(InvalidTokenError):
        _service().decode(token, "access")
