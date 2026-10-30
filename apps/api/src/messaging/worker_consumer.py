from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.models import OutboxMessage
from messaging.send_policy import SendPolicy


class OutboxConsumer:
    """Toma mensajes pendientes del outbox sin pisarse con otros workers (SKIP LOCKED).

    Aun no envia nada: en la Etapa 2 recibe el adaptador del canal y lo usa aqui.
    Espera que la transaccion ya tenga el inquilino fijado (core.tenant.set_tenant).
    """

    def __init__(self, policy: SendPolicy, batch_size: int = 10) -> None:
        self._policy = policy
        self._batch_size = batch_size

    async def fetch_batch(self, session: AsyncSession) -> Sequence[OutboxMessage]:
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.status == "pending")
            .order_by(OutboxMessage.created_at)
            .with_for_update(skip_locked=True)
            .limit(self._batch_size)
        )
        return (await session.execute(stmt)).scalars().all()

    async def apply_policy(self, session: AsyncSession, tenant_id: str) -> int:
        """Marca como bloqueados los mensajes que la politica rechaza. Devuelve cuantos reviso."""
        items = await self.fetch_batch(session)
        for item in items:
            decision = self._policy.evaluate(tenant_id, str(item.conversation_id), item.payload)
            if not decision.allowed:
                item.status = "blocked"
                item.blocked_reason = decision.reason
        await session.flush()
        return len(items)
