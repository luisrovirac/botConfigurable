"""Ingreso del webhook: guarda lo recibido y responde rapido. El worker procesa despues."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.tenant import set_tenant
from core.tenant_directory import TenantDirectory
from messaging.models import ChannelAccount, Message, MessageStatusEvent, WebhookEvent
from messaging.whatsapp_payload import InboundMessage, StatusUpdate, WebhookPayload

# Orden de los estados de entrega: un aviso viejo que llega tarde no hace retroceder el estado.
_STATUS_RANK = {"pending": 0, "sent": 1, "delivered": 2, "read": 3, "failed": 4}


@dataclass
class IngestResult:
    stored: int = 0
    duplicates: int = 0
    statuses: int = 0
    unknown_channels: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class _Channel:
    tenant_id: str
    channel_account_id: UUID


class WebhookIngestor:
    def __init__(self, directory: TenantDirectory, debounce: timedelta) -> None:
        self._directory = directory
        self._debounce = debounce

    async def ingest(self, session: AsyncSession, payload: WebhookPayload) -> IngestResult:
        result = IngestResult()
        channels: dict[str, _Channel | None] = {}
        for inbound in payload.inbound_messages():
            channel = await self._channel(session, channels, inbound.phone_number_id, result)
            if channel is not None:
                await self._store_message(session, channel, inbound, result)
        for status in payload.status_updates():
            channel = await self._channel(session, channels, status.phone_number_id, result)
            if channel is not None:
                await self._store_status(session, channel, status, result)
        return result

    async def _channel(
        self,
        session: AsyncSession,
        cache: dict[str, _Channel | None],
        phone_number_id: str | None,
        result: IngestResult,
    ) -> _Channel | None:
        key = phone_number_id or ""
        if key not in cache:
            cache[key] = await self._resolve(session, key)
        channel = cache[key]
        if channel is None:
            result.unknown_channels.add(key)
            return None
        await set_tenant(session, channel.tenant_id)
        return channel

    async def _resolve(self, session: AsyncSession, phone_number_id: str) -> _Channel | None:
        tenant_id = await self._directory.resolve_by_phone_number_id(session, phone_number_id)
        if tenant_id is None:
            return None
        await set_tenant(session, tenant_id)
        account_id = await session.scalar(
            select(ChannelAccount.id).where(
                ChannelAccount.provider == "whatsapp",
                ChannelAccount.phone_number_id == phone_number_id,
            )
        )
        return None if account_id is None else _Channel(tenant_id, account_id)

    async def _store_message(
        self,
        session: AsyncSession,
        channel: _Channel,
        inbound: InboundMessage,
        result: IngestResult,
    ) -> None:
        process_after = datetime.now(UTC) + self._debounce
        inserted = await session.scalar(
            insert(WebhookEvent)
            .values(
                tenant_id=channel.tenant_id,
                channel_account_id=channel.channel_account_id,
                provider_message_id=inbound.provider_message_id,
                sender_phone=inbound.sender_phone,
                payload=inbound.raw,
                process_after=process_after,
            )
            .on_conflict_do_nothing(constraint="uq_webhook_event_tenant_provider_msg")
            .returning(WebhookEvent.id)
        )
        if inserted is None:
            result.duplicates += 1
            return
        result.stored += 1
        # Debounce: los mensajes seguidos del mismo remitente se procesan juntos.
        await session.execute(
            update(WebhookEvent)
            .where(
                WebhookEvent.sender_phone == inbound.sender_phone,
                WebhookEvent.status == "pending",
            )
            .values(process_after=process_after)
        )

    async def _store_status(
        self, session: AsyncSession, channel: _Channel, status: StatusUpdate, result: IngestResult
    ) -> None:
        inserted = await session.scalar(
            insert(MessageStatusEvent)
            .values(
                tenant_id=channel.tenant_id,
                provider_message_id=status.provider_message_id,
                status=status.status,
                payload=status.raw,
            )
            .on_conflict_do_nothing(constraint="uq_message_status_event")
            .returning(MessageStatusEvent.id)
        )
        if inserted is None:
            return
        result.statuses += 1
        message = await session.scalar(
            select(Message).where(Message.provider_message_id == status.provider_message_id)
        )
        if message is not None and _rank(status.status) > _rank(message.status):
            message.status = status.status


def _rank(status: str | None) -> int:
    return _STATUS_RANK.get(status or "pending", 0)
