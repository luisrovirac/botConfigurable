from uuid import UUID, uuid4

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin


class ConsentEvent(Base, TenantMixin, TimestampMixin):
    __tablename__ = "consent_event"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    contact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    text_exact: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # opt-in/opt-out


class SuppressionList(Base, TenantMixin):
    __tablename__ = "suppression_list"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
