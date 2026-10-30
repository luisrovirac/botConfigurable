"""OutboxSender contra la base real, como bot_app y con el inquilino fijado."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from factories import PHONE_NUMBER_ID, TENANT_A
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from consent.models import SuppressionList
from core.tenant import set_tenant
from messaging.adapters.fake import FakeChannelAdapter
from messaging.conversation_store import ConversationStore
from messaging.dead_letter import DeadLetterService
from messaging.lock import lock_conversation
from messaging.models import (
    ChannelAccount,
    Contact,
    Conversation,
    DeadLetter,
    Message,
    OutboxMessage,
)
from messaging.outbox import OutboxWriter
from messaging.outbox_sender import OutboxSender, RetryPolicy
from messaging.ports.channel import ChannelAdapter, PermanentSendError, TransientSendError
from messaging.send_policy import MessagingWindowRule, RuleBasedPolicy, SuppressionRule

pytestmark = pytest.mark.usefixtures("tenants")

PHONE = "5215550000001"


class AlwaysTransient:
    async def send_text(self, sender_id: str, to: str, text: str) -> str:
        raise TransientSendError("503")

    def capabilities(self) -> dict[str, bool]:
        return {}


class AlwaysPermanent:
    async def send_text(self, sender_id: str, to: str, text: str) -> str:
        raise PermanentSendError("numero invalido")

    def capabilities(self) -> dict[str, bool]:
        return {}


def _sender(adapter: ChannelAdapter, max_attempts: int = 3, batch_size: int = 20) -> OutboxSender:
    return OutboxSender(
        adapter=adapter,
        policy=RuleBasedPolicy([SuppressionRule(), MessagingWindowRule(timedelta(hours=24))]),
        conversations=ConversationStore(),
        dead_letters=DeadLetterService(),
        retry=RetryPolicy(max_attempts=max_attempts, base_delay=timedelta(seconds=10)),
        batch_size=batch_size,
    )


async def _setup(
    sessions: async_sessionmaker[AsyncSession],
    kind: str = "reply",
    inbound_age: timedelta = timedelta(minutes=1),
    with_channel: bool = True,
    count: int = 1,
) -> UUID:
    """Conversacion con un entrante de hace `inbound_age` y `count` respuestas encoladas."""
    async with sessions() as session, session.begin():
        await set_tenant(session, TENANT_A)
        channel_id = await session.scalar(
            select(ChannelAccount.id).where(ChannelAccount.phone_number_id == PHONE_NUMBER_ID)
        )
        contact = Contact(tenant_id=TENANT_A, phone=PHONE)
        session.add(contact)
        await session.flush()
        conversation = Conversation(
            tenant_id=TENANT_A,
            contact_id=contact.id,
            channel_account_id=channel_id if with_channel else None,
        )
        session.add(conversation)
        await session.flush()
        session.add(
            Message(
                tenant_id=TENANT_A,
                conversation_id=conversation.id,
                direction="inbound",
                body="Hola",
                created_at=datetime.now(UTC) - inbound_age,
            )
        )
        for index in range(count):
            await OutboxWriter().enqueue_text(
                session, TENANT_A, conversation.id, PHONE, f"respuesta {index}", f"k{index}", kind
            )
        return conversation.id


async def _send(sessions: async_sessionmaker[AsyncSession], sender: OutboxSender) -> int:
    async with sessions() as session, session.begin():
        await set_tenant(session, TENANT_A)
        return await sender.send_due(session, TENANT_A)


async def _state(sessions: async_sessionmaker[AsyncSession]) -> tuple[OutboxMessage, Message]:
    async with sessions() as session:
        await set_tenant(session, TENANT_A)
        outbox = (await session.execute(select(OutboxMessage))).scalar_one()
        message = (
            await session.execute(select(Message).where(Message.direction == "outbound"))
        ).scalar_one()
        return outbox, message


async def test_sends_through_the_conversation_channel(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    adapter = FakeChannelAdapter()
    await _setup(app_sessions)

    assert await _send(app_sessions, _sender(adapter)) == 1

    outbox, message = await _state(app_sessions)
    (sent,) = adapter.sent
    assert (sent.sender_id, sent.to, sent.text) == (PHONE_NUMBER_ID, PHONE, "respuesta 0")
    assert outbox.status == "sent"
    assert message.status == "sent"
    assert message.provider_message_id == sent.provider_message_id


async def test_blocks_outside_the_24h_window(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    adapter = FakeChannelAdapter()
    await _setup(app_sessions, inbound_age=timedelta(hours=25))

    await _send(app_sessions, _sender(adapter))

    outbox, message = await _state(app_sessions)
    assert adapter.sent == []
    assert (outbox.status, outbox.blocked_reason) == ("blocked", "blocked_window")
    assert message.status == "blocked_window"


async def test_blocks_suppressed_contacts_but_not_the_opt_out_confirmation(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    adapter = FakeChannelAdapter()
    await _setup(app_sessions, kind="opt_out_confirmation")
    async with app_sessions() as session, session.begin():
        await set_tenant(session, TENANT_A)
        session.add(SuppressionList(tenant_id=TENANT_A, phone=PHONE, reason="opt-out"))
        await OutboxWriter().enqueue_text(
            session,
            TENANT_A,
            (await session.execute(select(Conversation.id))).scalar_one(),
            PHONE,
            "promo",
            "k-promo",
        )

    await _send(app_sessions, _sender(adapter))

    assert [m.text for m in adapter.sent] == ["respuesta 0"]
    async with app_sessions() as session:
        await set_tenant(session, TENANT_A)
        promo = await session.scalar(
            select(OutboxMessage).where(OutboxMessage.idempotency_key == "k-promo")
        )
    assert promo is not None
    assert promo.blocked_reason == "blocked_consent"


async def test_transient_failure_is_retried_later(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(app_sessions)

    await _send(app_sessions, _sender(AlwaysTransient()))

    outbox, message = await _state(app_sessions)
    assert outbox.status == "pending"
    assert outbox.attempts == 1
    assert outbox.scheduled_at > datetime.now(UTC)
    assert message.status == "pending"
    # Reprogramado: no se toma de nuevo hasta su hora.
    assert await _send(app_sessions, _sender(AlwaysTransient())) == 0


async def test_gives_up_after_max_attempts_and_moves_to_dead_letter(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(app_sessions)
    sender = _sender(AlwaysTransient(), max_attempts=2)
    await _send(app_sessions, sender)
    async with app_sessions() as session, session.begin():
        await set_tenant(session, TENANT_A)
        await session.execute(update(OutboxMessage).values(scheduled_at=datetime.now(UTC)))

    await _send(app_sessions, sender)

    outbox, message = await _state(app_sessions)
    assert (outbox.status, outbox.attempts, message.status) == ("failed", 2, "failed")
    async with app_sessions() as session:
        await set_tenant(session, TENANT_A)
        dead = (await session.execute(select(DeadLetter))).scalar_one()
    assert dead.outbox_message_id == outbox.id


async def test_permanent_failure_goes_straight_to_dead_letter(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(app_sessions)

    await _send(app_sessions, _sender(AlwaysPermanent()))

    outbox, message = await _state(app_sessions)
    assert (outbox.status, message.status) == ("failed", "failed")


async def test_conversation_without_channel_fails(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(app_sessions, with_channel=False)

    await _send(app_sessions, _sender(FakeChannelAdapter()))

    outbox, _ = await _state(app_sessions)
    assert outbox.status == "failed"


async def test_skip_locked_lets_two_workers_take_different_rows(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(app_sessions, count=2)
    first_adapter, second_adapter = FakeChannelAdapter(), FakeChannelAdapter()

    async with app_sessions() as first, first.begin():
        await set_tenant(first, TENANT_A)
        await _sender(first_adapter, batch_size=1).send_due(first, TENANT_A)
        async with app_sessions() as second, second.begin():
            await set_tenant(second, TENANT_A)
            await _sender(second_adapter, batch_size=1).send_due(second, TENANT_A)

    texts = {m.text for m in first_adapter.sent} | {m.text for m in second_adapter.sent}
    assert len(first_adapter.sent) == len(second_adapter.sent) == 1
    assert texts == {"respuesta 0", "respuesta 1"}


async def test_conversation_lock_serializes_transactions(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    conversation_id = UUID(int=1)
    order: list[str] = []

    async def hold(label: str, delay: float) -> None:
        async with app_sessions() as session, session.begin():
            await lock_conversation(session, TENANT_A, conversation_id)
            order.append(f"{label}:start")
            await asyncio.sleep(delay)
            order.append(f"{label}:end")

    first = asyncio.create_task(hold("a", 0.3))
    await asyncio.sleep(0.1)
    await hold("b", 0)
    await first
    assert order == ["a:start", "a:end", "b:start", "b:end"]


async def test_dead_letter_is_stored_without_committing(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session:
        await set_tenant(session, TENANT_A)
        await DeadLetterService().move(session, TENANT_A, None, "timeout")
        assert (await session.execute(select(DeadLetter))).first() is not None
        await session.rollback()  # quien llama decide: si no confirma, no queda nada

        await set_tenant(session, TENANT_A)
        assert (await session.execute(select(DeadLetter))).first() is None
