from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import CreatedAtMixin, TenantMixin, TimestampMixin
from core.types import JSONDict


class ChannelAccount(Base, TenantMixin, TimestampMixin):
    """Numero/cuenta de un canal que pertenece a un inquilino (p. ej. un numero de WhatsApp).

    `phone_number_id` es unico en toda la plataforma: con el se resuelve el inquilino de cada
    webhook (funcion SQL resolve_tenant_by_phone_number_id).
    """

    __tablename__ = "channel_account"
    __table_args__ = (
        UniqueConstraint("provider", "phone_number_id", name="uq_channel_account_provider_phone"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String)  # whatsapp
    phone_number_id: Mapped[str] = mapped_column(String)
    display_number: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))


class WebhookEvent(Base, TenantMixin, TimestampMixin):
    """Mensaje entrante tal como llego. Es la cola de entrada que procesa el worker."""

    __tablename__ = "webhook_event"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "provider_message_id", name="uq_webhook_event_tenant_provider_msg"
        ),
        Index("ix_webhook_event_pending", "status", "process_after"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    channel_account_id: Mapped[UUID | None] = mapped_column(ForeignKey("channel_account.id"))
    provider_message_id: Mapped[str | None] = mapped_column(String)
    sender_phone: Mapped[str | None] = mapped_column(String)
    payload: Mapped[JSONDict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String, server_default="pending")  # pending/done/failed
    process_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text)


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
    channel_account_id: Mapped[UUID | None] = mapped_column(ForeignKey("channel_account.id"))
    kind: Mapped[str] = mapped_column(String, server_default="direct")
    assigned_to: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, server_default="bot")


class Message(Base, TenantMixin):
    __tablename__ = "message"
    __table_args__ = (
        Index("ix_message_conversation_created", "conversation_id", "created_at"),
        Index("ix_message_provider_message_id", "provider_message_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversation.id"))
    direction: Mapped[str] = mapped_column(String)  # inbound/outbound
    body: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String, server_default="text")
    # Salientes: pending, sent, delivered, read, failed, blocked_window, blocked_consent.
    status: Mapped[str | None] = mapped_column(String)
    provider_message_id: Mapped[str | None] = mapped_column(String)
    # clock_timestamp() y no now(): los mensajes de una misma transaccion (entrante y sus
    # respuestas) quedan con horas distintas y crecientes, y el inbox los ordena bien.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


class MessageStatusEvent(Base, TenantMixin, CreatedAtMixin):
    """Avisos de entrega que manda el proveedor (sent, delivered, read, failed)."""

    __tablename__ = "message_status_event"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "provider_message_id", "status", name="uq_message_status_event"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_message_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    payload: Mapped[JSONDict] = mapped_column(JSONB)


class OutboxMessage(Base, TenantMixin, CreatedAtMixin):
    """Mensaje saliente pendiente de enviar. Lo crea el flujo y lo envia el worker."""

    __tablename__ = "outbox_message"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_outbox_idempotency"),
        Index("ix_outbox_message_pending", "status", "scheduled_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversation.id"))
    message_id: Mapped[UUID | None] = mapped_column(ForeignKey("message.id"))
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
