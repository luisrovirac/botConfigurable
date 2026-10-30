from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.tenant import set_tenant


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_tenant_id(x_tenant_id: str = Header(..., alias="X-Tenant-ID")) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID required")
    return x_tenant_id


async def get_tenant_session(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    await set_tenant(session, tenant_id)
    yield session
