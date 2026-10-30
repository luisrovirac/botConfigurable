from typing import Any

import pytest
from pydantic import ValidationError

from core.config import Settings

REQUIRED: dict[str, Any] = {
    "database_url": "postgresql+asyncpg://u:p@h/db",
    "whatsapp_verify_token": "verify",
    "whatsapp_app_secret": "secret",
}
STRONG_KEY = "x" * 32


def _settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **{**REQUIRED, **overrides})


def test_development_accepts_weak_secret_key() -> None:
    assert _settings(environment="development", secret_key="change-me").is_local


@pytest.mark.parametrize("weak", ["change-me", "corta"])
def test_production_rejects_weak_secret_key(weak: str) -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _settings(environment="production", secret_key=weak)


def test_production_accepts_strong_secret_key() -> None:
    assert not _settings(environment="production", secret_key=STRONG_KEY).is_local


@pytest.mark.parametrize("missing", ["whatsapp_app_secret", "whatsapp_verify_token"])
def test_whatsapp_secrets_are_required(missing: str) -> None:
    with pytest.raises(ValidationError):
        _settings(secret_key=STRONG_KEY, **{missing: ""})


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(environment="prod", secret_key=STRONG_KEY)
