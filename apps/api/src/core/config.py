from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]

_WEAK_SECRET_KEYS = {"", "change-me", "changeme", "secret"}
_MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    """Configuracion de la app. Se valida al arrancar: si falta algo critico, no arranca."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "botConfigurable"
    environment: Environment = "development"
    debug: bool = False

    # Conexion de la app: rol sin privilegios, sujeto a RLS.
    database_url: str = Field(min_length=1)
    # Conexion del dueno de las tablas, solo para migraciones. Si falta, se usa database_url.
    database_owner_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = Field(min_length=1)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)

    whatsapp_verify_token: str = Field(min_length=1)
    whatsapp_app_secret: str = Field(min_length=1)
    meta_api_version: str = "v21.0"
    # Temporal hasta la Etapa 2 (channel_account): inquilino al que van los mensajes entrantes.
    whatsapp_default_tenant_id: str = Field(default="demo", min_length=1)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @property
    def is_local(self) -> bool:
        return self.environment in ("development", "test")

    @model_validator(mode="after")
    def _require_strong_secrets_outside_local(self) -> "Settings":
        if self.is_local:
            return self
        if self.secret_key in _WEAK_SECRET_KEYS or len(self.secret_key) < _MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY debe tener al menos {_MIN_SECRET_KEY_LENGTH} caracteres "
                "aleatorios fuera de development/test (genera una con: openssl rand -hex 32)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    # Los valores obligatorios vienen del entorno o de .env.
    return Settings()
