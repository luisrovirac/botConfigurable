from uuid import uuid4

import pytest
from conftest import TEST_PASSWORD, login
from factories import TENANT_A, TENANT_B
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth.models import User
from messaging.models import Contact, Conversation, Message

pytestmark = pytest.mark.usefixtures("tenants")


async def _conversation(
    sessions: async_sessionmaker[AsyncSession], tenant_id: str, phone: str, bodies: list[str]
) -> str:
    async with sessions() as session, session.begin():
        contact = Contact(tenant_id=tenant_id, phone=phone, name=f"Cliente {phone}")
        session.add(contact)
        await session.flush()
        conversation = Conversation(tenant_id=tenant_id, contact_id=contact.id)
        session.add(conversation)
        await session.flush()
        for index, body in enumerate(bodies):
            direction = "inbound" if index % 2 == 0 else "outbound"
            session.add(
                Message(
                    tenant_id=tenant_id,
                    conversation_id=conversation.id,
                    direction=direction,
                    body=body,
                    status=None if direction == "inbound" else "sent",
                )
            )
            await session.flush()
        return str(conversation.id)


async def test_login_returns_tokens_with_the_users_tenant(client: AsyncClient) -> None:
    headers = await login(client)
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["tenant_id"] == TENANT_A
    assert me.json()["role"] == "admin"


@pytest.mark.parametrize(
    ("email", "password"),
    [("admin@a.test", "incorrecta"), ("nadie@a.test", TEST_PASSWORD), ("ADMIN@A.TEST", "x")],
)
async def test_login_rejects_bad_credentials_with_the_same_message(
    client: AsyncClient, email: str, password: str
) -> None:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Email o contrasena incorrectos"


async def test_login_email_is_case_insensitive(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": "ADMIN@A.TEST", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200


async def test_inactive_user_cannot_log_in(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    async with owner_sessions() as session, session.begin():
        await session.execute(update(User).values(is_active=False))
    response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@a.test", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401


async def test_refresh_issues_new_tokens_and_rejects_access_tokens(client: AsyncClient) -> None:
    tokens = (
        await client.post(
            "/api/v1/auth/login", json={"email": "admin@a.test", "password": TEST_PASSWORD}
        )
    ).json()

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    with_access = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert refreshed.status_code == 200
    assert {"access_token", "refresh_token"} <= refreshed.json().keys()
    assert with_access.status_code == 401


async def test_refresh_fails_if_user_was_deactivated(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    tokens = (
        await client.post(
            "/api/v1/auth/login", json={"email": "admin@a.test", "password": TEST_PASSWORD}
        )
    ).json()
    async with owner_sessions() as session, session.begin():
        await session.execute(update(User).values(is_active=False))

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


@pytest.mark.parametrize("header", [None, "Bearer token-falso"])
async def test_inbox_requires_a_valid_token(client: AsyncClient, header: str | None) -> None:
    headers = {"Authorization": header} if header else {}
    response = await client.get("/api/v1/conversations", headers=headers)
    assert response.status_code == 401


async def test_inbox_lists_only_the_users_tenant_most_recent_first(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    older = await _conversation(owner_sessions, TENANT_A, "111", ["hola"])
    newer = await _conversation(owner_sessions, TENANT_A, "222", ["buenas", "respuesta"])
    await _conversation(owner_sessions, TENANT_B, "333", ["de otro inquilino"])

    response = await client.get("/api/v1/conversations", headers=await login(client))

    items = response.json()
    assert [item["id"] for item in items] == [newer, older]
    assert items[0]["contact_phone"] == "222"
    assert items[0]["last_message_body"] == "respuesta"
    assert items[0]["last_message_direction"] == "outbound"


async def test_messages_are_returned_in_order_with_status(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    conversation_id = await _conversation(owner_sessions, TENANT_A, "111", ["hola", "menu", "1"])

    response = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=await login(client)
    )

    assert response.status_code == 200
    assert [(m["body"], m["direction"], m["status"]) for m in response.json()] == [
        ("hola", "inbound", None),
        ("menu", "outbound", "sent"),
        ("1", "inbound", None),
    ]


async def test_messages_of_another_tenant_are_not_found(
    client: AsyncClient, owner_sessions: async_sessionmaker[AsyncSession]
) -> None:
    foreign = await _conversation(owner_sessions, TENANT_B, "333", ["privado"])
    headers = await login(client)

    for conversation_id in (foreign, str(uuid4())):
        response = await client.get(
            f"/api/v1/conversations/{conversation_id}/messages", headers=headers
        )
        assert response.status_code == 404
