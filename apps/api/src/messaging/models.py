from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import CreatedAtMixin, TenantMixin, TimestampMixin
from core.types import JSONDict


class WebhookEvent(Base, TenantMixin, TimestampMixin):
    __tablename__ = "webhook_event"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "provider_message_id", name="uq_webhook_event_tenant_provider_msg"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    channel_account_id: Mapped[str | None] = mapped_column(String)
    provider_message_id: Mapped[str | None] = mapped_column(String)
    payload: Mapped[JSONDict] = mapped_column(JSONB)
    processed: Mapped[bool] = mapped_column(server_default=text("false"))


class Contact(Base, TenantMixin, TimestampMixin):
    __tablename__ = "contact"
    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_contact_tenant_phone"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    phone: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)


class Conversation(Base, TenantMixin, TimestampMixin):
    __tablename__ = "conversation"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    contact_id: Mapped[UUID] = mapped_column(ForeignKey("contact.id"))
    kind: Mapped[str] = mapped_column(String, server_default="direct")
    assigned_to: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, server_default="bot")


class Message(Base, TenantMixin, CreatedAtMixin):
    __tablename__ = "message"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversation.id"))
    direction: Mapped[str] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String, server_default="text")


class OutboxMessage(Base, TenantMixin, CreatedAtMixin):
    __tablename__ = "outbox_message"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_outbox_idempotency"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversation.id"))
    payload: Mapped[JSONDict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String, server_default="pending")
    idempotency_key: Mapped[str] = mapped_column(String)
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    blocked_reason: Mapped[str | None] = mapped_column(String)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DeadLetter(Base, TenantMixin, CreatedAtMixin):
    __tablename__ = "dead_letter"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    outbox_message_id: Mapped[UUID | None] = mapped_column(ForeignKey("outbox_message.id"))
    error: Mapped[str | None] = mapped_column(Text)
