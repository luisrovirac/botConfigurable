from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin
from core.types import JSONDict


class Lead(Base, TenantMixin, TimestampMixin):
    __tablename__ = "lead"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    contact_id: Mapped[UUID] = mapped_column(ForeignKey("contact.id"))
    source: Mapped[str] = mapped_column(String)
    utm: Mapped[JSONDict] = mapped_column(JSONB, default=dict)
    score: Mapped[float] = mapped_column(server_default=text("0"))
    stage: Mapped[str] = mapped_column(String, server_default="new")
    assigned_to: Mapped[str | None] = mapped_column(String)
    ghl_contact_id: Mapped[str | None] = mapped_column(String)
