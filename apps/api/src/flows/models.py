from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.models import TenantMixin, TimestampMixin
from core.types import JSONDict


class FlowInstance(Base, TenantMixin, TimestampMixin):
    """Estado persistido de un flujo (FSM) en una conversacion."""

    __tablename__ = "flow_instance"
    __table_args__ = (UniqueConstraint("conversation_id", name="uq_flow_instance_conversation"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversation.id"))
    pack_version: Mapped[str] = mapped_column(String)
    current_node: Mapped[str] = mapped_column(String)
    variables: Mapped[JSONDict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
