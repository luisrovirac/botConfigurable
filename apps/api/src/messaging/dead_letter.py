from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from messaging.models import DeadLetter


class DeadLetterService:
    """Aparta un mensaje que no se pudo enviar. No hace commit: lo hace quien llama."""

    async def move(
        self, session: AsyncSession, tenant_id: str, outbox_message_id: UUID | None, error: str
    ) -> None:
        session.add(
            DeadLetter(tenant_id=tenant_id, outbox_message_id=outbox_message_id, error=error)
        )
        await session.flush()
