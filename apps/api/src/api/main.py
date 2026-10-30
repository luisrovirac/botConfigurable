from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.health import router as health_router
from api.v1 import auth, conversations, webhook
from auth.jwt import TokenService
from auth.password import PasswordService
from auth.service import AuthService
from core.config import Settings, get_settings
from core.db import create_engine, create_session_factory
from core.logging import configure_logging
from core.tenant_directory import TenantDirectory
from messaging.webhook_ingest import WebhookIngestor

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Composition root de la API: crea los recursos compartidos y registra las rutas."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved = settings or get_settings()
        configure_logging(resolved.log_level)
        engine = create_engine(resolved.database_url)
        app.state.settings = resolved
        app.state.session_factory = create_session_factory(engine)
        _wire_services(app, resolved)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="botConfigurable", version="0.2.0", lifespan=lifespan)
    app.include_router(health_router)
    for router in (webhook.router, auth.router, conversations.router):
        app.include_router(router, prefix=API_PREFIX)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


def _wire_services(app: FastAPI, settings: Settings) -> None:
    directory = TenantDirectory()
    tokens = TokenService(
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        access_ttl=timedelta(minutes=settings.access_token_expire_minutes),
        refresh_ttl=timedelta(days=settings.refresh_token_expire_days),
    )
    app.state.auth_service = AuthService(directory, PasswordService(), tokens)
    app.state.webhook_ingestor = WebhookIngestor(directory, settings.inbound_debounce)


app = create_app()
