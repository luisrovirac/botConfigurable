from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.tenant import set_tenant
from messaging.models import OutboxMessage
from messaging.send_policy import SendPolicy


class OutboxConsumer:
    def __init__(self) -> None:
        self.policy = SendPolicy()

    async def fetch_batch(self, session: AsyncSession, tenant_id: str, limit: int = 10):
        await set_tenant(session, tenant_id)
        # SELECT ... FOR UPDATE SKIP LOCKED
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.tenant_id == tenant_id, OutboxMessage.status == "pending")
            .order_by(OutboxMessage.created_at)
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    async def process(self, session: AsyncSession, tenant_id: str) -> int:
        items = await self.fetch_batch(session, tenant_id)
        count = 0
        for item in items:
            decision = self.policy.evaluate(tenant_id, str(item.conversation_id), item.payload)
            if not decision.allowed:
                item.status = "blocked"
                item.blocked_reason = decision.reason
                count += 1
                continue
            item.status = "sent"
            item.attempts += 1
            count += 1
        await session.commit()
        return count
