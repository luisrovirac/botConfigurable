from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.models import Message, OutboxMessage


class OutboxWriter:
    """Encola mensajes salientes. El worker los envia despues (OutboxSender).

    Crea tambien el `message` saliente con estado 'pending', para que el inbox lo muestre
    desde ya. Es idempotente por `idempotency_key`: reprocesar el mismo entrante no duplica.
    """

    async def enqueue_text(
        self,
        session: AsyncSession,
        tenant_id: str,
        conversation_id: UUID,
        to: str,
        body: str,
        idempotency_key: str,
        kind: str = "reply",
    ) -> bool:
        """Devuelve False si ya existia un mensaje con esa clave."""
        exists = await session.scalar(
            select(OutboxMessage.id).where(OutboxMessage.idempotency_key == idempotency_key)
        )
        if exists is not None:
            return False
        message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            direction="outbound",
            body=body,
            type="text",
            status="pending",
        )
        session.add(message)
        await session.flush()
        session.add(
            OutboxMessage(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                message_id=message.id,
                payload={"type": "text", "to": to, "body": body, "kind": kind},
                idempotency_key=idempotency_key,
            )
        )
        await session.flush()
        return True
