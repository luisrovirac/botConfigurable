from datetime import timedelta
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
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Conexion de la app: rol sin privilegios, sujeto a RLS.
    database_url: str = Field(min_length=1)
    # Conexion del dueno de las tablas, solo para migraciones y seed. Si falta, database_url.
    database_owner_url: str | None = None

    secret_key: str = Field(min_length=1)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)

    # WhatsApp Cloud API
    whatsapp_verify_token: str = Field(min_length=1)
    whatsapp_app_secret: str = Field(min_length=1)
    # fake: registra el envio sin llamar a Meta (desarrollo sin credenciales). real: Graph API.
    whatsapp_send_mode: Literal["fake", "real"] = "fake"
    whatsapp_access_token: str = ""
    whatsapp_api_base_url: str = "https://graph.facebook.com"
    meta_api_version: str = "v21.0"

    # Mensajeria
    flow_path: str = "packs/demo/flow.yaml"
    inbound_debounce_ms: int = Field(default=1500, ge=0)
    messaging_window_hours: int = Field(default=24, gt=0)
    outbox_max_attempts: int = Field(default=5, gt=0)
    opt_out_keywords: str = "BAJA,STOP"
    opt_in_keywords: str = "ALTA,START"
    opt_out_confirmation_text: str = (
        "Listo, no te enviaremos mas mensajes. Si cambias de opinion, escribe ALTA."
    )
    opt_in_confirmation_text: str = "Listo, vuelves a recibir nuestros mensajes."
    worker_poll_interval_ms: int = Field(default=500, gt=0)

    @property
    def is_local(self) -> bool:
        return self.environment in ("development", "test")

    @property
    def inbound_debounce(self) -> timedelta:
        return timedelta(milliseconds=self.inbound_debounce_ms)

    @property
    def messaging_window(self) -> timedelta:
        return timedelta(hours=self.messaging_window_hours)

    @property
    def opt_out_keyword_set(self) -> frozenset[str]:
        return _keywords(self.opt_out_keywords)

    @property
    def opt_in_keyword_set(self) -> frozenset[str]:
        return _keywords(self.opt_in_keywords)

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if self.whatsapp_send_mode == "real" and not self.whatsapp_access_token:
            raise ValueError("WHATSAPP_SEND_MODE=real requiere WHATSAPP_ACCESS_TOKEN")
        if self.is_local:
            return self
        if self.secret_key in _WEAK_SECRET_KEYS or len(self.secret_key) < _MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY debe tener al menos {_MIN_SECRET_KEY_LENGTH} caracteres "
                "aleatorios fuera de development/test (genera una con: openssl rand -hex 32)"
            )
        return self


def _keywords(raw: str) -> frozenset[str]:
    return frozenset(word.strip().upper() for word in raw.split(",") if word.strip())


@lru_cache
def get_settings() -> Settings:
    # Los valores obligatorios vienen del entorno o de .env.
    return Settings()
