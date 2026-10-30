from uuid import UUID, uuid4

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin


class Lead(Base, TenantMixin, TimestampMixin):
    __tablename__ = "lead"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    contact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contact.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    utm: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(String, default="new")
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True)
    ghl_contact_id: Mapped[str | None] = mapped_column(String, nullable=True)
