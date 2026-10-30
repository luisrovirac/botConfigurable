import pytest
from factories import (
    TEST_APP_SECRET,
    TEST_VERIFY_TOKEN,
    signature_headers,
    signed,
    whatsapp_text_payload,
)
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from messaging.models import Contact, Conversation, Message, WebhookEvent

pytestmark = pytest.mark.usefixtures("clean_db")


async def _post(
    client: AsyncClient, message_id: str, body: str = "Hola", name: str | None = "Ana"
) -> int:
    payload = whatsapp_text_payload(message_id, body=body, name=name)
    content, headers = signed(payload, TEST_APP_SECRET)
    response = await client.post("/webhook/whatsapp", content=content, headers=headers)
    return response.status_code


async def _count(sessions: async_sessionmaker[AsyncSession], model: type) -> int:
    async with sessions() as session:
        return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_verification_returns_challenge_with_meta_query_names(client: AsyncClient) -> None:
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": TEST_VERIFY_TOKEN,
            "hub.challenge": "1234",
        },
    )
    assert response.status_code == 200
    assert response.text == "1234"


async def test_verification_rejects_wrong_token(client: AsyncClient) -> None:
    response = await client.get(
        "/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "1234"},
    )
    assert response.status_code == 403


async def test_rejects_unsigned_message(client: AsyncClient) -> None:
    response = await client.post("/webhook/whatsapp", json=whatsapp_text_payload("wamid.1"))
    assert response.status_code == 403


async def test_rejects_invalid_json_even_if_signed(client: AsyncClient) -> None:
    body = b"no es json"
    response = await client.post(
        "/webhook/whatsapp", content=body, headers=signature_headers(body, TEST_APP_SECRET)
    )
    assert response.status_code == 400


async def test_stores_message_contact_and_conversation(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    assert await _post(client, "wamid.1", body="Hola") == 200

    async with owner_sessions() as session:
        message = (await session.execute(select(Message))).scalar_one()
        contact = (await session.execute(select(Contact))).scalar_one()
    assert message.body == "Hola"
    assert message.direction == "inbound"
    assert message.tenant_id == "tenant-a"
    assert contact.phone == "5215550000001"
    assert contact.name == "Ana"


async def test_replayed_webhook_does_not_duplicate(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    assert await _post(client, "wamid.1") == 200
    assert await _post(client, "wamid.1") == 200

    assert await _count(owner_sessions, Message) == 1
    assert await _count(owner_sessions, WebhookEvent) == 1


async def test_same_sender_reuses_contact_and_conversation(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    assert await _post(client, "wamid.1", name=None) == 200
    assert await _post(client, "wamid.2", name="Ana Perez") == 200

    assert await _count(owner_sessions, Contact) == 1
    assert await _count(owner_sessions, Conversation) == 1
    assert await _count(owner_sessions, Message) == 2
    async with owner_sessions() as session:
        assert await session.scalar(select(Contact.name)) == "Ana Perez"
