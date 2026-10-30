"""Criterio de aceptacion de la Fase 0 (plan maestro 7, plan de mejoras Etapa 2).

Flujo completo con la API y el worker reales; solo el envio a Meta es falso:
mensaje firmado -> cola -> worker (flujo + politica) -> envio -> inbox.
"""

from datetime import UTC, datetime, timedelta

import pytest
from conftest import login
from factories import (
    TENANT_A,
    TEST_APP_SECRET,
    signed,
    whatsapp_status_payload,
    whatsapp_text_payload,
)
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.tenant import set_tenant
from core.types import JSONDict
from messaging.adapters.fake import FakeChannelAdapter
from messaging.models import Conversation, Message, OutboxMessage
from messaging.outbox import OutboxWriter
from messaging.worker_cycle import WorkerCycle

pytestmark = pytest.mark.usefixtures("tenants")

CLIENT_PHONE = "5215550000001"


async def _webhook(client: AsyncClient, payload: JSONDict) -> None:
    content, headers = signed(payload, TEST_APP_SECRET)
    response = await client.post("/api/v1/webhook/whatsapp", content=content, headers=headers)
    assert response.status_code == 200


async def _say(client: AsyncClient, worker: WorkerCycle, message_id: str, body: str) -> None:
    await _webhook(client, whatsapp_text_payload(message_id, sender=CLIENT_PHONE, body=body))
    while await worker.run_once():
        pass


async def _inbox_messages(client: AsyncClient) -> list[JSONDict]:
    headers = await login(client)
    (conversation,) = (await client.get("/api/v1/conversations", headers=headers)).json()
    response = await client.get(
        f"/api/v1/conversations/{conversation['id']}/messages", headers=headers
    )
    messages: list[JSONDict] = response.json()
    return messages


async def test_message_gets_an_answer_and_shows_in_the_inbox(
    client: AsyncClient, worker: WorkerCycle, fake_adapter: FakeChannelAdapter
) -> None:
    await _say(client, worker, "wamid.1", "Hola")
    await _say(client, worker, "wamid.2", "1")

    sent = [m.text for m in fake_adapter.sent]
    assert sent[0].startswith("Hola Ana, soy el asistente virtual")
    assert sent[1].startswith("Atendemos de lunes a viernes")
    assert sent[2] == sent[0]  # vuelve al menu
    assert all(m.to == CLIENT_PHONE for m in fake_adapter.sent)

    messages = await _inbox_messages(client)
    assert [(m["direction"], m["status"]) for m in messages] == [
        ("inbound", None),
        ("outbound", "sent"),
        ("inbound", None),
        ("outbound", "sent"),
        ("outbound", "sent"),
    ]
    assert messages[3]["body"] == sent[1]


async def test_replayed_webhook_duplicates_nothing(
    client: AsyncClient,
    worker: WorkerCycle,
    fake_adapter: FakeChannelAdapter,
    owner_sessions: async_sessionmaker[AsyncSession],
) -> None:
    for _ in range(3):
        await _say(client, worker, "wamid.1", "Hola")

    async with owner_sessions() as session:
        messages = await session.scalar(select(func.count()).select_from(Message))
        outbox = await session.scalar(select(func.count()).select_from(OutboxMessage))
    assert (messages, outbox, len(fake_adapter.sent)) == (2, 1, 1)


async def test_reply_outside_the_24h_window_is_blocked_and_visible(
    client: AsyncClient,
    worker: WorkerCycle,
    fake_adapter: FakeChannelAdapter,
    owner_sessions: async_sessionmaker[AsyncSession],
    app_sessions: async_sessionmaker[AsyncSession],
) -> None:
    await _say(client, worker, "wamid.1", "Hola")
    # Pasan 25 horas sin que el cliente escriba: la ventana de servicio se cierra.
    async with owner_sessions() as session, session.begin():
        await session.execute(
            update(Message).where(Message.direction == "inbound").values(created_at=_in(hours=-25))
        )
    # Un mensaje tardio (p. ej. un aviso del negocio) ya no puede salir sin plantilla.
    async with app_sessions() as session, session.begin():
        await set_tenant(session, TENANT_A)
        conversation_id = (await session.execute(select(Conversation.id))).scalar_one()
        await OutboxWriter().enqueue_text(
            session, TENANT_A, conversation_id, CLIENT_PHONE, "Tu pedido esta listo", "tarde-1"
        )
    await worker.run_once()

    assert len(fake_adapter.sent) == 1  # solo el saludo, cuando la ventana estaba abierta
    messages = await _inbox_messages(client)
    assert messages[-1]["body"] == "Tu pedido esta listo"
    assert messages[-1]["status"] == "blocked_window"


async def test_opt_out_keyword_confirms_and_suppresses_later_replies(
    client: AsyncClient, worker: WorkerCycle, fake_adapter: FakeChannelAdapter
) -> None:
    await _say(client, worker, "wamid.1", "Hola")
    await _say(client, worker, "wamid.2", "baja")
    await _say(client, worker, "wamid.3", "1")

    assert len(fake_adapter.sent) == 2
    assert fake_adapter.sent[1].text.startswith("Listo, no te enviaremos mas mensajes")
    statuses = [m["status"] for m in await _inbox_messages(client) if m["direction"] == "outbound"]
    assert statuses[-1] == "blocked_consent"

    await _say(client, worker, "wamid.4", "ALTA")
    assert fake_adapter.sent[-1].text == "Listo, vuelves a recibir nuestros mensajes."


async def test_delivery_status_from_meta_updates_the_inbox(
    client: AsyncClient, worker: WorkerCycle, fake_adapter: FakeChannelAdapter
) -> None:
    await _say(client, worker, "wamid.1", "Hola")

    await _webhook(
        client, whatsapp_status_payload(fake_adapter.sent[0].provider_message_id, "read")
    )

    messages = await _inbox_messages(client)
    assert messages[-1]["status"] == "read"


def _in(hours: float) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours)
