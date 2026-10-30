from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def set_tenant(session: AsyncSession, tenant_id: str) -> None:
    await session.execute(text("SET LOCAL app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
