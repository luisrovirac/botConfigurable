from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin


class Campaign(Base, TenantMixin, TimestampMixin):
    __tablename__ = "campaign"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    template_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft")
    segment: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CampaignRecipient(Base, TenantMixin):
    __tablename__ = "campaign_recipient"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("campaign.id"), nullable=False)
    contact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contact.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
