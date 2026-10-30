"""El rol de la app (bot_app) solo ve y escribe datos del inquilino fijado en la transaccion."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.models import Tenant
from core.tenant import set_tenant
from messaging.models import Contact
from packs.models import Pack

pytestmark = pytest.mark.usefixtures("clean_db")


@pytest.fixture
async def two_tenants(clean_db: None, owner_sessions: async_sessionmaker[AsyncSession]) -> None:
    async with owner_sessions() as session, session.begin():
        session.add_all(
            [
                Tenant(id="tenant-a", name="A"),
                Tenant(id="tenant-b", name="B"),
                Contact(tenant_id="tenant-a", phone="111"),
                Contact(tenant_id="tenant-b", phone="222"),
            ]
        )


async def _visible_phones(session: AsyncSession) -> list[str | None]:
    return list((await session.execute(select(Contact.phone).order_by(Contact.phone))).scalars())


@pytest.mark.usefixtures("two_tenants")
async def test_each_tenant_sees_only_its_own_rows(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session, session.begin():
        await set_tenant(session, "tenant-a")
        assert await _visible_phones(session) == ["111"]
        assert list((await session.execute(select(Tenant.id))).scalars()) == ["tenant-a"]

    async with app_sessions() as session, session.begin():
        await set_tenant(session, "tenant-b")
        assert await _visible_phones(session) == ["222"]


@pytest.mark.usefixtures("two_tenants")
async def test_without_tenant_no_rows_are_visible(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session, session.begin():
        assert await session.scalar(select(func.count()).select_from(Contact)) == 0


@pytest.mark.usefixtures("two_tenants")
async def test_cannot_write_rows_of_another_tenant(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(DBAPIError, match="row-level security"):
        async with app_sessions() as session, session.begin():
            await set_tenant(session, "tenant-a")
            session.add(Contact(tenant_id="tenant-b", phone="333"))
            await session.flush()


async def test_tenant_setting_ends_with_the_transaction(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session:
        async with session.begin():
            await set_tenant(session, "tenant-a")
        async with session.begin():
            value = await session.scalar(text("SELECT current_setting('app.tenant_id', true)"))
    assert not value


async def test_app_role_cannot_modify_global_packs(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(DBAPIError, match="permission denied"):
        async with app_sessions() as session, session.begin():
            session.add(Pack(id="nuevo", name="Nuevo"))
            await session.flush()


async def test_app_role_cannot_read_migration_table(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(DBAPIError, match="permission denied"):
        async with app_sessions() as session, session.begin():
            await session.execute(text("SELECT * FROM alembic_version"))


async def test_app_role_is_not_privileged(app_sessions: async_sessionmaker[AsyncSession]) -> None:
    async with app_sessions() as session:
        row = (
            await session.execute(
                text(
                    "SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            )
        ).one()
    assert tuple(row) == (False, False, False, False)
