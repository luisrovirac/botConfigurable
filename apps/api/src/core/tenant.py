from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant(session: AsyncSession, tenant_id: str) -> None:
    """Fija el inquilino de la transaccion actual; las politicas RLS filtran por el.

    `SET LOCAL` no acepta parametros, por eso se usa set_config(..., is_local=true).
    El valor dura hasta el commit o rollback de la transaccion.
    """
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": tenant_id},
    )
