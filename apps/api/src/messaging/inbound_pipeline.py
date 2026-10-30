from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.models import Contact, Conversation, Message, WebhookEvent
from messaging.whatsapp_payload import InboundMessage, WebhookPayload


class InboundPipeline:
    """Guarda los mensajes entrantes. Es idempotente: un reenvio de Meta no duplica nada.

    No hace commit: la transaccion (y el inquilino fijado en ella) la maneja quien llama.
    """

    async def process(self, session: AsyncSession, tenant_id: str, payload: WebhookPayload) -> int:
        """Devuelve cuantos mensajes nuevos se guardaron."""
        stored = 0
        for inbound in payload.inbound_messages():
            if not await self._register_event(session, tenant_id, inbound):
                continue  # ya recibido antes
            contact_id = await self._upsert_contact(session, tenant_id, inbound)
            conversation_id = await self._conversation_for(session, tenant_id, contact_id)
            session.add(
                Message(
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    direction="inbound",
                    body=inbound.body,
                    type=inbound.type,
                )
            )
            stored += 1
        await session.flush()
        return stored

    async def _register_event(
        self, session: AsyncSession, tenant_id: str, inbound: InboundMessage
    ) -> bool:
        """Registra el evento; False si ese provider_message_id ya existia."""
        stmt = (
            insert(WebhookEvent)
            .values(
                tenant_id=tenant_id,
                provider_message_id=inbound.provider_message_id,
                payload=inbound.raw,
                processed=True,
            )
            .on_conflict_do_nothing(constraint="uq_webhook_event_tenant_provider_msg")
            .returning(WebhookEvent.id)
        )
        return (await session.execute(stmt)).scalar_one_or_none() is not None

    async def _upsert_contact(
        self, session: AsyncSession, tenant_id: str, inbound: InboundMessage
    ) -> UUID:
        values = insert(Contact).values(
            tenant_id=tenant_id, phone=inbound.sender_phone, name=inbound.sender_name
        )
        upsert = values.on_conflict_do_update(
            constraint="uq_contact_tenant_phone",
            set_={"name": func.coalesce(values.excluded.name, Contact.name)},
        ).returning(Contact.id)
        contact_id: UUID = (await session.execute(upsert)).scalar_one()
        return contact_id

    async def _conversation_for(
        self, session: AsyncSession, tenant_id: str, contact_id: UUID
    ) -> UUID:
        existing = await session.scalar(
            select(Conversation.id)
            .where(Conversation.tenant_id == tenant_id, Conversation.contact_id == contact_id)
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            return existing
        conversation = Conversation(tenant_id=tenant_id, contact_id=contact_id, kind="direct")
        session.add(conversation)
        await session.flush()
        return conversation.id
