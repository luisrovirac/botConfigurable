from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin


class WebhookEvent(Base, TenantMixin, TimestampMixin):
    __tablename__ = "webhook_event"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    channel_account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Contact(Base, TenantMixin, TimestampMixin):
    __tablename__ = "contact"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)


class Conversation(Base, TenantMixin, TimestampMixin):
    __tablename__ = "conversation"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    contact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contact.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, default="direct", nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="bot", nullable=False)


class Message(Base, TenantMixin):
    __tablename__ = "message"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("conversation.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String, default="text", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxMessage(Base, TenantMixin):
    __tablename__ = "outbox_message"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("conversation.id"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeadLetter(Base, TenantMixin):
    __tablename__ = "dead_letter"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    outbox_message_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
