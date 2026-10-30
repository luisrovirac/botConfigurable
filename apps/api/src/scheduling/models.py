from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin


class Service(Base, TenantMixin, TimestampMixin):
    __tablename__ = "service"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String)
    duration_minutes: Mapped[int]
    price: Mapped[int | None]  # en la unidad minima de la moneda (centavos)


class Resource(Base, TenantMixin, TimestampMixin):
    __tablename__ = "resource"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # professional/sala/equipo


class Appointment(Base, TenantMixin, TimestampMixin):
    __tablename__ = "appointment"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    contact_id: Mapped[UUID] = mapped_column(ForeignKey("contact.id"))
    service_id: Mapped[UUID] = mapped_column(ForeignKey("service.id"))
    resource_id: Mapped[UUID | None] = mapped_column(ForeignKey("resource.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, server_default="pending")
    external_event_id: Mapped[str | None] = mapped_column(String)
    sync_token: Mapped[str | None] = mapped_column(String)
