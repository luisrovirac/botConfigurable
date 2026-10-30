from datetime import UTC, datetime, timedelta

import pytest
from factories import (
    PHONE_NUMBER_ID,
    TENANT_A,
    TEST_APP_SECRET,
    TEST_VERIFY_TOKEN,
    signature_headers,
    signed,
    whatsapp_status_payload,
    whatsapp_text_payload,
)
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.types import JSONDict
from messaging.models import Contact, Conversation, Message, MessageStatusEvent, WebhookEvent

pytestmark = pytest.mark.usefixtures("tenants")

URL = "/api/v1/webhook/whatsapp"


async def _post(client: AsyncClient, payload: JSONDict) -> int:
    content, headers = signed(payload, TEST_APP_SECRET)
    return (await client.post(URL, content=content, headers=headers)).status_code


async def _count(sessions: async_sessionmaker[AsyncSession], model: type) -> int:
    async with sessions() as session:
        return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_verification_returns_challenge_with_meta_query_names(client: AsyncClient) -> None:
    params = {"hub.mode": "subscribe", "hub.verify_token": TEST_VERIFY_TOKEN, "hub.challenge": "1"}
    response = await client.get(URL, params=params)
    assert response.status_code == 200
    assert response.text == "1"


async def test_verification_rejects_wrong_token(client: AsyncClient) -> None:
    params = {"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "1"}
    assert (await client.get(URL, params=params)).status_code == 403


async def test_rejects_unsigned_message(client: AsyncClient) -> None:
    response = await client.post(URL, json=whatsapp_text_payload("wamid.1"))
    assert response.status_code == 403


async def test_rejects_invalid_json_even_if_signed(client: AsyncClient) -> None:
    body = b"no es json"
    response = await client.post(
        URL, content=body, headers=signature_headers(body, TEST_APP_SECRET)
    )
    assert response.status_code == 400


async def test_queues_message_for_the_tenant_that_owns_the_number(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    assert await _post(client, whatsapp_text_payload("wamid.1", body="Hola")) == 200

    async with owner_sessions() as session:
        event = (await session.execute(select(WebhookEvent))).scalar_one()
    assert event.tenant_id == TENANT_A
    assert event.status == "pending"
    assert event.sender_phone == "5215550000001"
    assert event.payload["text"]["body"] == "Hola"
    assert event.payload["profile_name"] == "Ana"
    # El webhook solo encola: los mensajes los crea el worker.
    assert await _count(owner_sessions, Message) == 0


async def test_unknown_number_is_acknowledged_but_not_stored(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    payload = whatsapp_text_payload("wamid.1", phone_number_id="NO_REGISTRADO")
    assert await _post(client, payload) == 200
    assert await _count(owner_sessions, WebhookEvent) == 0


async def test_replayed_webhook_does_not_duplicate(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    assert await _post(client, whatsapp_text_payload("wamid.1")) == 200
    assert await _post(client, whatsapp_text_payload("wamid.1")) == 200
    assert await _count(owner_sessions, WebhookEvent) == 1


async def test_new_message_postpones_pending_ones_of_the_same_sender(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    assert await _post(client, whatsapp_text_payload("wamid.1")) == 200
    past = datetime.now(UTC) - timedelta(hours=1)
    async with owner_sessions() as session, session.begin():
        await session.execute(update(WebhookEvent).values(process_after=past))

    assert await _post(client, whatsapp_text_payload("wamid.2")) == 200

    async with owner_sessions() as session:
        times = (await session.execute(select(WebhookEvent.process_after))).scalars().all()
    assert len(set(times)) == 1  # ambos se procesaran juntos
    assert times[0] > past


async def test_status_update_advances_message_status(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    async with owner_sessions() as session, session.begin():
        contact = Contact(tenant_id=TENANT_A, phone="5215550000001")
        session.add(contact)
        await session.flush()
        conversation = Conversation(tenant_id=TENANT_A, contact_id=contact.id)
        session.add(conversation)
        await session.flush()
        session.add(
            Message(
                tenant_id=TENANT_A,
                conversation_id=conversation.id,
                direction="outbound",
                status="sent",
                provider_message_id="wamid.out",
            )
        )

    for status in ("read", "delivered", "read"):  # llega tarde un aviso viejo y uno repetido
        assert await _post(client, whatsapp_status_payload("wamid.out", status)) == 200

    async with owner_sessions() as session:
        assert await session.scalar(select(Message.status)) == "read"
    assert await _count(owner_sessions, MessageStatusEvent) == 2


async def test_status_for_unknown_message_is_recorded(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    payload = whatsapp_status_payload("wamid.desconocido", "delivered", PHONE_NUMBER_ID)
    assert await _post(client, payload) == 200
    assert await _count(owner_sessions, MessageStatusEvent) == 1
