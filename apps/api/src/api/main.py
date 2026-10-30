from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis

from api.health import router as health_router
from api.v1 import auth, webhook
from core.config import Settings, get_settings
from core.db import create_engine, create_session_factory
from core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Composition root de la API: crea los recursos compartidos y registra las rutas."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved = settings or get_settings()
        configure_logging(resolved.log_level)
        engine = create_engine(resolved.database_url)
        redis = Redis.from_url(resolved.redis_url)
        app.state.settings = resolved
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = redis
        try:
            yield
        finally:
            await redis.aclose()
            await engine.dispose()

    app = FastAPI(title="botConfigurable", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(webhook.router)
    app.include_router(auth.router)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
