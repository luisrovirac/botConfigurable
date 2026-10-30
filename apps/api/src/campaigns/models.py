from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin
from core.types import JSONDict


class Campaign(Base, TenantMixin, TimestampMixin):
    __tablename__ = "campaign"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String)
    template_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, server_default="draft")
    segment: Mapped[JSONDict] = mapped_column(JSONB, default=dict)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignRecipient(Base, TenantMixin):
    __tablename__ = "campaign_recipient"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaign.id"))
    contact_id: Mapped[UUID] = mapped_column(ForeignKey("contact.id"))
    status: Mapped[str] = mapped_column(String, server_default="pending")
    reason: Mapped[str | None] = mapped_column(String)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
