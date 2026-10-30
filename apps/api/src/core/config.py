from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "botConfigurable"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # Conexion de la app: rol sin privilegios, sujeto a RLS.
    database_url: str = Field(...)
    # Conexion del dueno de las tablas, solo para migraciones. Si falta, se usa database_url.
    database_owner_url: str | None = Field(default=None)
    redis_url: str = Field(default="redis://localhost:6379/0")

    secret_key: str = Field(...)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=7)

    whatsapp_verify_token: str = Field(default="")
    whatsapp_app_secret: str = Field(default="")
    meta_api_version: str = Field(default="v21.0")

    log_level: str = Field(default="INFO")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("database_url required")
        return v


def get_settings() -> Settings:
    return Settings()
