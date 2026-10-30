"""Fixtures compartidas.

Los tests de integracion usan una base real (botconfigurable_test): las migraciones corren
con el dueno de las tablas y la app se conecta como bot_app, asi RLS se aplica de verdad.
Correr con: scripts\\test.bat (dentro de Docker) o en CI.
"""

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from factories import (
    PHONE_NUMBER_ID,
    TENANT_A,
    TENANT_B,
    TEST_APP_SECRET,
    TEST_VERIFY_TOKEN,
)
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from api.main import create_app
from auth.models import User
from auth.password import PasswordService
from core.config import Settings
from core.db import create_engine, create_session_factory
from core.models import Tenant
from messaging.adapters.fake import FakeChannelAdapter
from messaging.factory import build_worker_cycle
from messaging.models import ChannelAccount
from messaging.worker_cycle import WorkerCycle

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_PASSWORD = "clave-de-prueba"


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
        secret_key="test-secret-key-de-32-caracteres!",
        whatsapp_verify_token=TEST_VERIFY_TOKEN,
        whatsapp_app_secret=TEST_APP_SECRET,
        whatsapp_send_mode="fake",
        inbound_debounce_ms=0,
        flow_path=str(REPO_ROOT / "packs" / "demo" / "flow.yaml"),
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


@pytest.fixture
async def tenants(clean_db: None, owner_sessions: async_sessionmaker[AsyncSession]) -> None:
    """Dos inquilinos; tenant-a tiene el numero de WhatsApp PHONE_NUMBER_ID y un admin."""
    passwords = PasswordService()
    async with owner_sessions() as session, session.begin():
        session.add_all([Tenant(id=TENANT_A, name="A"), Tenant(id=TENANT_B, name="B")])
        await session.flush()
        session.add_all(
            [
                ChannelAccount(
                    tenant_id=TENANT_A, provider="whatsapp", phone_number_id=PHONE_NUMBER_ID
                ),
                ChannelAccount(
                    tenant_id=TENANT_B, provider="whatsapp", phone_number_id="PHONE_ID_B"
                ),
                User(
                    tenant_id=TENANT_A,
                    email="admin@a.test",
                    password_hash=passwords.hash(TEST_PASSWORD),
                    role="admin",
                ),
                User(
                    tenant_id=TENANT_B,
                    email="admin@b.test",
                    password_hash=passwords.hash(TEST_PASSWORD),
                    role="admin",
                ),
            ]
        )


@pytest.fixture
def fake_adapter() -> FakeChannelAdapter:
    return FakeChannelAdapter()


@pytest.fixture
def worker(
    settings: Settings,
    app_sessions: async_sessionmaker[AsyncSession],
    fake_adapter: FakeChannelAdapter,
) -> WorkerCycle:
    """El worker real, con el adaptador falso (registra los envios en fake_adapter.sent)."""
    return build_worker_cycle(settings, app_sessions, fake_adapter)


async def login(client: AsyncClient, email: str = "admin@a.test") -> dict[str, str]:
    """Cabeceras con el token de acceso del usuario."""
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
