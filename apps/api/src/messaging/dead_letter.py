from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from messaging.models import DeadLetter


class DeadLetterService:
    async def move(self, session: AsyncSession, tenant_id: str, outbox_id: str | None, error: str) -> None:
        entry = DeadLetter(tenant_id=tenant_id, outbox_message_id=outbox_id, error=error)
        session.add(entry)
        await session.commit()
