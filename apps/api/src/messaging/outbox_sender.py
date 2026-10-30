"""Envia los mensajes pendientes del outbox, aplicando la politica de envio."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from consent.models import SuppressionList
from core.metrics import OUTBOX_PROCESSED
from messaging.conversation_store import ConversationStore
from messaging.dead_letter import DeadLetterService
from messaging.models import ChannelAccount, Conversation, Message, OutboxMessage
from messaging.ports.channel import ChannelAdapter, PermanentSendError, TransientSendError
from messaging.send_policy import SendContext, SendPolicy

logger = structlog.get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    base_delay: timedelta = timedelta(seconds=2)

    def delay(self, attempts: int) -> timedelta:
        return self.base_delay * (1 << max(attempts - 1, 0))


class OutboxSender:
    def __init__(
        self,
        adapter: ChannelAdapter,
        policy: SendPolicy,
        conversations: ConversationStore,
        dead_letters: DeadLetterService,
        retry: RetryPolicy,
        batch_size: int = 20,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._adapter = adapter
        self._policy = policy
        self._conversations = conversations
        self._dead_letters = dead_letters
        self._retry = retry
        self._batch_size = batch_size
        self._clock = clock

    async def send_due(self, session: AsyncSession, tenant_id: str) -> int:
        """Envia los mensajes vencidos del inquilino fijado en la sesion. Devuelve cuantos."""
        items = await self._claim(session)
        for item in items:
            await self._send_one(session, tenant_id, item)
        await session.flush()
        return len(items)

    async def _claim(self, session: AsyncSession) -> Sequence[OutboxMessage]:
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.status == "pending", OutboxMessage.scheduled_at <= self._clock())
            .order_by(OutboxMessage.created_at)
            .with_for_update(skip_locked=True)
            .limit(self._batch_size)
        )
        return (await session.execute(stmt)).scalars().all()

    async def _send_one(self, session: AsyncSession, tenant_id: str, item: OutboxMessage) -> None:
        message = await session.get(Message, item.message_id) if item.message_id else None
        decision = self._policy.evaluate(await self._context(session, item))
        if not decision.allowed:
            _finish(item, message, "blocked", decision.reason)
            item.blocked_reason = decision.reason
            return
        try:
            sender_id = await self._sender_id(session, item)
            provider_id = await self._adapter.send_text(
                sender_id, item.payload["to"], item.payload["body"]
            )
        except TransientSendError as exc:
            await self._retry_or_fail(session, tenant_id, item, message, exc)
        except PermanentSendError as exc:
            await self._fail(session, tenant_id, item, message, exc)
        else:
            item.attempts += 1
            _finish(item, message, "sent", "sent")
            if message is not None:
                message.provider_message_id = provider_id

    async def _context(self, session: AsyncSession, item: OutboxMessage) -> SendContext:
        suppressed = await session.scalar(
            select(exists().where(SuppressionList.phone == item.payload["to"]))
        )
        return SendContext(
            kind=str(item.payload.get("kind", "reply")),
            suppressed=bool(suppressed),
            last_inbound_at=await self._conversations.last_inbound_at(
                session, item.conversation_id
            ),
            now=self._clock(),
        )

    async def _sender_id(self, session: AsyncSession, item: OutboxMessage) -> str:
        sender_id = await session.scalar(
            select(ChannelAccount.phone_number_id)
            .join(Conversation, Conversation.channel_account_id == ChannelAccount.id)
            .where(Conversation.id == item.conversation_id)
        )
        if sender_id is None:
            raise PermanentSendError("La conversacion no tiene cuenta de canal asociada")
        return sender_id

    async def _retry_or_fail(
        self,
        session: AsyncSession,
        tenant_id: str,
        item: OutboxMessage,
        message: Message | None,
        error: TransientSendError,
    ) -> None:
        item.attempts += 1
        if item.attempts >= self._retry.max_attempts:
            await self._fail(session, tenant_id, item, message, error)
            return
        item.scheduled_at = self._clock() + self._retry.delay(item.attempts)
        OUTBOX_PROCESSED.labels(status="retry").inc()
        logger.warning("outbox_retry", outbox_id=str(item.id), attempts=item.attempts)

    async def _fail(
        self,
        session: AsyncSession,
        tenant_id: str,
        item: OutboxMessage,
        message: Message | None,
        error: Exception,
    ) -> None:
        _finish(item, message, "failed", "failed")
        await self._dead_letters.move(session, tenant_id, item.id, str(error))
        logger.error("outbox_failed", outbox_id=str(item.id), error=str(error))


def _finish(
    item: OutboxMessage, message: Message | None, outbox_status: str, message_status: str | None
) -> None:
    item.status = outbox_status
    if message is not None:
        message.status = message_status
    OUTBOX_PROCESSED.labels(status=outbox_status).inc()
