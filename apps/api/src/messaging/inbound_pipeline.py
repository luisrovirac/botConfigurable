from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.models import Contact, Conversation, Message, WebhookEvent


class InboundPipeline:
    async def process(self, session: AsyncSession, tenant_id: str, payload: dict) -> None:
        # Idempotencia por provider_message_id
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return
        msg = messages[0]
        provider_id = msg.get("id")
        from_num = msg.get("from")
        body = msg.get("text", {}).get("body", "")

        # Crear/obtener contacto
        res = await session.execute(select(Contact).where(Contact.tenant_id == tenant_id, Contact.phone == from_num))
        contact = res.scalar_one_or_none()
        if not contact:
            contact = Contact(tenant_id=tenant_id, phone=from_num)
            session.add(contact)
            await session.flush()

        # Crear/obtener conversación
        res = await session.execute(
            select(Conversation).where(Conversation.tenant_id == tenant_id, Conversation.contact_id == contact.id)
        )
        conv = res.scalar_one_or_none()
        if not conv:
            conv = Conversation(tenant_id=tenant_id, contact_id=contact.id, kind="direct")
            session.add(conv)
            await session.flush()

        # Guardar mensaje
        message = Message(
            tenant_id=tenant_id, conversation_id=conv.id, direction="inbound", body=body, type="text"
        )
        session.add(message)

        # Registrar webhook_event si no existe
        if provider_id:
            res = await session.execute(
                select(WebhookEvent).where(
                    WebhookEvent.tenant_id == tenant_id, WebhookEvent.provider_message_id == provider_id
                )
            )
            if not res.scalar_one_or_none():
                event = WebhookEvent(
                    tenant_id=tenant_id,
                    provider_message_id=provider_id,
                    payload=payload,
                    processed=True,
                )
                session.add(event)

        await session.commit()
