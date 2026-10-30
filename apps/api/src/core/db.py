from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    global engine, SessionLocal
    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def tenant_session(session: AsyncSession, tenant_id: str):
    await session.execute(text("SET LOCAL app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
    try:
        yield session
    finally:
        pass
