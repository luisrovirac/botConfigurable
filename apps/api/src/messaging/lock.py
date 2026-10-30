from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def conversation_lock(session: AsyncSession, conversation_id: UUID | str):
    key = int(hash(str(conversation_id)) % (2**31))
    await session.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
    try:
        yield
    finally:
        await session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
