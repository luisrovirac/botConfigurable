"""Servicios de mensajeria contra la base real, como bot_app y con el inquilino fijado."""

import asyncio
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.tenant import set_tenant
from core.types import JSONDict
from messaging.dead_letter import DeadLetterService
from messaging.lock import lock_conversation
from messaging.models import Contact, Conversation, DeadLetter, OutboxMessage
from messaging.send_policy import AllowAllPolicy, SendDecision
from messaging.worker_consumer import OutboxConsumer

pytestmark = pytest.mark.usefixtures("clean_db")

TENANT = "tenant-a"


class BlockEverything:
    def evaluate(self, tenant_id: str, conversation_id: str, payload: JSONDict) -> SendDecision:
        return SendDecision(allowed=False, reason="blocked_window")


async def _conversation(session: AsyncSession) -> UUID:
    contact = Contact(tenant_id=TENANT, phone="111")
    session.add(contact)
    await session.flush()
    conversation = Conversation(tenant_id=TENANT, contact_id=contact.id)
    session.add(conversation)
    await session.flush()
    return conversation.id


async def _pending(session: AsyncSession, conversation_id: UUID, key: str) -> None:
    session.add(
        OutboxMessage(
            tenant_id=TENANT,
            conversation_id=conversation_id,
            payload={"type": "text", "body": "hola"},
            idempotency_key=key,
        )
    )
    await session.flush()


async def test_policy_blocks_pending_messages(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session, session.begin():
        await set_tenant(session, TENANT)
        conversation_id = await _conversation(session)
        await _pending(session, conversation_id, "k1")
        await _pending(session, conversation_id, "k2")

        reviewed = await OutboxConsumer(BlockEverything()).apply_policy(session, TENANT)

        rows = (await session.execute(select(OutboxMessage))).scalars().all()
    assert reviewed == 2
    assert {(row.status, row.blocked_reason) for row in rows} == {("blocked", "blocked_window")}


async def test_allow_all_policy_leaves_messages_pending(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session, session.begin():
        await set_tenant(session, TENANT)
        await _pending(session, await _conversation(session), "k1")

        await OutboxConsumer(AllowAllPolicy()).apply_policy(session, TENANT)

        status = await session.scalar(select(OutboxMessage.status))
    assert status == "pending"


async def test_skip_locked_lets_two_workers_take_different_rows(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as setup, setup.begin():
        await set_tenant(setup, TENANT)
        conversation_id = await _conversation(setup)
        for key in ("k1", "k2"):
            await _pending(setup, conversation_id, key)

    consumer = OutboxConsumer(AllowAllPolicy(), batch_size=1)
    async with app_sessions() as first, first.begin():
        await set_tenant(first, TENANT)
        taken_first = await consumer.fetch_batch(first)
        async with app_sessions() as second, second.begin():
            await set_tenant(second, TENANT)
            taken_second = await consumer.fetch_batch(second)
    assert len(taken_first) == len(taken_second) == 1
    assert taken_first[0].id != taken_second[0].id


async def test_dead_letter_is_stored_without_committing(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with app_sessions() as session:
        await set_tenant(session, TENANT)
        await DeadLetterService().move(session, TENANT, None, "timeout")
        assert (await session.execute(select(DeadLetter))).first() is not None
        await session.rollback()  # quien llama decide: si no confirma, no queda nada

        await set_tenant(session, TENANT)
        assert (await session.execute(select(DeadLetter))).first() is None


async def test_conversation_lock_serializes_transactions(
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    conversation_id = UUID(int=1)
    order: list[str] = []

    async def hold(label: str, delay: float) -> None:
        async with app_sessions() as session, session.begin():
            await lock_conversation(session, TENANT, conversation_id)
            order.append(f"{label}:start")
            await asyncio.sleep(delay)
            order.append(f"{label}:end")

    first = asyncio.create_task(hold("a", 0.3))
    await asyncio.sleep(0.1)
    await hold("b", 0)
    await first
    assert order == ["a:start", "a:end", "b:start", "b:end"]
