from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def lock_conversation(session: AsyncSession, tenant_id: str, conversation_id: UUID) -> None:
    """Bloquea la conversacion hasta el fin de la transaccion actual.

    La clave sale de hashtext() en Postgres, que es igual en todos los procesos
    (el hash() de Python cambia en cada proceso y no serviria entre API y worker).
    """
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"{tenant_id}:{conversation_id}"},
    )
