"""Fixtures compartidas.

Los tests de integracion usan una base real (botconfigurable_test): las migraciones corren
con el dueno de las tablas y la app se conecta como bot_app, asi RLS se aplica de verdad.
Correr con: scripts\\test.bat (dentro de Docker) o en CI.
"""

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from alembic import command
from alembic.config import Config
from factories import TEST_APP_SECRET, TEST_VERIFY_TOKEN
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from api.main import create_app
from core.config import Settings
from core.db import create_engine, create_session_factory


def _require_test_database(url: str) -> str:
    # Los tests vacian tablas: nunca deben apuntar a la base de desarrollo o produccion.
    if "_test" not in url.rsplit("/", 1)[-1]:
        pytest.exit(f"Los tests solo corren contra una base *_test (recibido: {url})", returncode=2)
    return url


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=_require_test_database(os.environ["DATABASE_URL"]),
        database_owner_url=_require_test_database(os.environ["DATABASE_OWNER_URL"]),
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        secret_key="test-secret-key",
        whatsapp_verify_token=TEST_VERIFY_TOKEN,
        whatsapp_app_secret=TEST_APP_SECRET,
        whatsapp_default_tenant_id="tenant-a",
        log_level="WARNING",
    )


@pytest.fixture(scope="session")
def migrated_database(settings: Settings) -> Iterator[None]:
    """Aplica todas las migraciones una vez por sesion de tests."""
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(scope="session")
async def owner_engine(settings: Settings, migrated_database: None) -> AsyncIterator[AsyncEngine]:
    assert settings.database_owner_url is not None
    engine = create_engine(settings.database_owner_url)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def app_engine(settings: Settings, migrated_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(settings.database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def clean_db(owner_engine: AsyncEngine) -> None:
    """Vacia todas las tablas de datos antes del test (como dueno, sin RLS)."""
    async with owner_engine.begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename <> 'alembic_version'"
                )
            )
        ).scalars()
        quoted = ", ".join(f'"{name}"' for name in tables)
        await conn.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))


@pytest.fixture
def app_sessions(app_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sesiones como bot_app (sujetas a RLS)."""
    return create_session_factory(app_engine)


@pytest.fixture
def owner_sessions(owner_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sesiones como dueno de las tablas (ve todo). Solo para preparar y revisar datos."""
    return create_session_factory(owner_engine)


@pytest.fixture
async def app(settings: Settings, migrated_database: None) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
