from seed import DemoData, seed_demo
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth.models import User
from auth.password import PasswordService
from core.models import Tenant
from messaging.models import ChannelAccount


async def test_seed_is_idempotent_and_keeps_existing_password(
    clean_db: None, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    data = DemoData(admin_password="primera")
    for password in ("primera", "segunda"):
        async with owner_sessions() as session, session.begin():
            await seed_demo(session, DemoData(admin_password=password))

    async with owner_sessions() as session:
        counts = [
            await session.scalar(select(func.count()).select_from(model))
            for model in (Tenant, ChannelAccount, User)
        ]
        user = (await session.execute(select(User))).scalar_one()
    assert counts == [1, 1, 1]
    assert user.email == data.admin_email
    assert PasswordService().verify("primera", user.password_hash)
