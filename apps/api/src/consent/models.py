from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin


class ConsentEvent(Base, TenantMixin, TimestampMixin):
    __tablename__ = "consent_event"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    contact_id: Mapped[UUID] = mapped_column(ForeignKey("contact.id"))
    channel: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    text_exact: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String)  # opt-in/opt-out


class SuppressionList(Base, TenantMixin):
    __tablename__ = "suppression_list"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    phone: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
