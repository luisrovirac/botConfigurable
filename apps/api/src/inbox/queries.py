"""Consultas de solo lectura del inbox. RLS limita todo al inquilino fijado en la sesion."""

from uuid import UUID

from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession

from inbox.schemas import ConversationSummary, MessageView
from messaging.models import Contact, Conversation, Message


class InboxQueries:
    async def conversations(self, session: AsyncSession, limit: int) -> list[ConversationSummary]:
        last_message = (
            select(Message.body, Message.direction, Message.created_at)
            .where(Message.conversation_id == Conversation.id)
            .order_by(Message.created_at.desc())
            .limit(1)
            .lateral("last_message")
        )
        stmt = (
            select(
                Conversation.id,
                Contact.phone.label("contact_phone"),
                Contact.name.label("contact_name"),
                Conversation.status,
                last_message.c.body.label("last_message_body"),
                last_message.c.direction.label("last_message_direction"),
                last_message.c.created_at.label("last_message_at"),
            )
            .join(Contact, Contact.id == Conversation.contact_id)
            .outerjoin(last_message, true())
            .order_by(last_message.c.created_at.desc().nulls_last())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).mappings()
        return [ConversationSummary.model_validate(dict(row)) for row in rows]

    async def messages(
        self, session: AsyncSession, conversation_id: UUID
    ) -> list[MessageView] | None:
        """Mensajes en orden cronologico, o None si la conversacion no existe (o es de otro)."""
        visible = await session.scalar(
            select(Conversation.id).where(Conversation.id == conversation_id)
        )
        if visible is None:
            return None
        rows = await session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return [MessageView.model_validate(row) for row in rows]
