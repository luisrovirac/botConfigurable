"""Acceso a contactos, conversaciones y mensajes. No hace commit (lo hace quien llama)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.models import Contact, Conversation, Message, WebhookEvent


@dataclass(frozen=True)
class StoredInbound:
    """Mensaje entrante tal como quedo en la cola (webhook_event)."""

    provider_message_id: str
    sender_phone: str
    sender_name: str | None
    type: str
    body: str | None

    @classmethod
    def from_event(cls, event: WebhookEvent) -> "StoredInbound":
        payload = event.payload
        text = payload.get("text")
        return cls(
            provider_message_id=event.provider_message_id or str(event.id),
            sender_phone=event.sender_phone or str(payload.get("from", "")),
            sender_name=payload.get("profile_name"),
            type=str(payload.get("type", "text")),
            body=text.get("body") if isinstance(text, dict) else None,
        )


class ConversationStore:
    async def upsert_contact(
        self, session: AsyncSession, tenant_id: str, phone: str, name: str | None
    ) -> UUID:
        values = insert(Contact).values(tenant_id=tenant_id, phone=phone, name=name)
        upsert = values.on_conflict_do_update(
            constraint="uq_contact_tenant_phone",
            set_={"name": func.coalesce(values.excluded.name, Contact.name)},
        ).returning(Contact.id)
        contact_id: UUID = (await session.execute(upsert)).scalar_one()
        return contact_id

    async def conversation_for(
        self,
        session: AsyncSession,
        tenant_id: str,
        contact_id: UUID,
        channel_account_id: UUID | None,
    ) -> UUID:
        """Conversacion mas reciente del contacto, o una nueva."""
        existing = await session.scalar(
            select(Conversation.id)
            .where(Conversation.contact_id == contact_id)
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            return existing
        conversation = Conversation(
            tenant_id=tenant_id,
            contact_id=contact_id,
            channel_account_id=channel_account_id,
            kind="direct",
        )
        session.add(conversation)
        await session.flush()
        return conversation.id

    def add_inbound(
        self, session: AsyncSession, tenant_id: str, conversation_id: UUID, inbound: StoredInbound
    ) -> None:
        session.add(
            Message(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                direction="inbound",
                body=inbound.body,
                type=inbound.type,
                provider_message_id=inbound.provider_message_id,
            )
        )

    async def last_inbound_at(
        self, session: AsyncSession, conversation_id: UUID
    ) -> datetime | None:
        """Ultimo mensaje del contacto: abre la ventana de servicio de 24 h."""
        last: datetime | None = await session.scalar(
            select(func.max(Message.created_at)).where(
                Message.conversation_id == conversation_id, Message.direction == "inbound"
            )
        )
        return last
