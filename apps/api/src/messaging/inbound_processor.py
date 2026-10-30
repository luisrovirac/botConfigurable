"""Procesa la cola de entrada (webhook_event): guarda, corre el flujo y encola respuestas."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import groupby
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from consent.service import ConsentIntent, ConsentService
from flows.definition import FlowDefinition
from flows.engine.fsm import FlowContext, FlowEngine
from flows.engine.instance_store import FlowInstanceStore
from messaging.conversation_store import ConversationStore, StoredInbound
from messaging.lock import lock_conversation
from messaging.models import WebhookEvent
from messaging.outbox import OutboxWriter


@dataclass(frozen=True)
class Reply:
    text: str
    kind: str = "reply"


@dataclass(frozen=True)
class ConsentReplies:
    opt_out: str
    opt_in: str


@dataclass(frozen=True)
class _Turn:
    """Lo que escribio un contacto en un lote (varios mensajes seguidos por el debounce)."""

    tenant_id: str
    contact_id: UUID
    conversation_id: UUID
    phone: str
    last: StoredInbound


class InboundProcessor:
    def __init__(
        self,
        conversations: ConversationStore,
        flow: FlowDefinition,
        engine: FlowEngine,
        instances: FlowInstanceStore,
        outbox: OutboxWriter,
        consent: ConsentService,
        consent_replies: ConsentReplies,
        batch_size: int = 50,
    ) -> None:
        self._conversations = conversations
        self._flow = flow
        self._engine = engine
        self._instances = instances
        self._outbox = outbox
        self._consent = consent
        self._consent_replies = consent_replies
        self._batch_size = batch_size

    async def process_due(self, session: AsyncSession, tenant_id: str) -> int:
        """Procesa los eventos vencidos del inquilino fijado en la sesion. Devuelve cuantos."""
        events = await self._claim(session)
        by_sender = groupby(events, key=lambda event: event.sender_phone or "")
        for _, group in by_sender:
            await self._process_sender(session, tenant_id, list(group))
        return len(events)

    async def _claim(self, session: AsyncSession) -> Sequence[WebhookEvent]:
        stmt = (
            select(WebhookEvent)
            .where(
                WebhookEvent.status == "pending",
                WebhookEvent.process_after <= datetime.now(UTC),
            )
            .order_by(WebhookEvent.sender_phone, WebhookEvent.created_at)
            .with_for_update(skip_locked=True)
            .limit(self._batch_size)
        )
        return (await session.execute(stmt)).scalars().all()

    async def _process_sender(
        self, session: AsyncSession, tenant_id: str, events: list[WebhookEvent]
    ) -> None:
        inbound = [StoredInbound.from_event(event) for event in events]
        last = inbound[-1]
        contact_id = await self._conversations.upsert_contact(
            session, tenant_id, last.sender_phone, last.sender_name
        )
        conversation_id = await self._conversations.conversation_for(
            session, tenant_id, contact_id, events[0].channel_account_id
        )
        await lock_conversation(session, tenant_id, conversation_id)
        for message in inbound:
            self._conversations.add_inbound(session, tenant_id, conversation_id, message)
        turn = _Turn(tenant_id, contact_id, conversation_id, last.sender_phone, last)
        for index, reply in enumerate(await self._replies(session, turn)):
            await self._outbox.enqueue_text(
                session,
                tenant_id,
                conversation_id,
                to=turn.phone,
                body=reply.text,
                idempotency_key=f"{tenant_id}:{last.provider_message_id}:{index}",
                kind=reply.kind,
            )
        for event in events:
            event.status = "done"
            event.attempts += 1
        await session.flush()

    async def _replies(self, session: AsyncSession, turn: _Turn) -> list[Reply]:
        intent = self._consent.intent(turn.last.body)
        if intent is not None:
            await self._consent.record(
                session, turn.tenant_id, turn.contact_id, turn.phone, intent, turn.last.body or ""
            )
            if intent is ConsentIntent.OPT_OUT:
                return [Reply(self._consent_replies.opt_out, kind="opt_out_confirmation")]
            return [Reply(self._consent_replies.opt_in, kind="opt_in_confirmation")]
        return [Reply(text) for text in await self._run_flow(session, turn)]

    async def _run_flow(self, session: AsyncSession, turn: _Turn) -> list[str]:
        context = FlowContext({"nombre": turn.last.sender_name or ""})
        current = await self._instances.current_node(session, turn.conversation_id)
        if current is None:
            outcome = self._engine.start(self._flow, context)
        else:
            outcome = self._engine.advance(self._flow, current, turn.last.body or "", context)
        await self._instances.save(
            session, turn.tenant_id, turn.conversation_id, self._flow.key, outcome.current_node
        )
        return outcome.replies
