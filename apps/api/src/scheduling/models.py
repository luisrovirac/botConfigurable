from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin


class Service(Base, TenantMixin, TimestampMixin):
    __tablename__ = "service"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float | None] = mapped_column(Integer, nullable=True)


class Resource(Base, TenantMixin, TimestampMixin):
    __tablename__ = "resource"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # professional/sala/equipo


class Appointment(Base, TenantMixin, TimestampMixin):
    __tablename__ = "appointment"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    contact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contact.id"), nullable=False)
    service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("service.id"), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("resource.id"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sync_token: Mapped[str | None] = mapped_column(String, nullable=True)
