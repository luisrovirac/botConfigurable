from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_phone: str | None
    contact_name: str | None
    status: str
    last_message_body: str | None
    last_message_direction: str | None
    last_message_at: datetime | None


class MessageView(BaseModel):
    """Mensaje en el inbox. `status` en salientes: pending, sent, delivered, read, failed,
    blocked_window o blocked_consent."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    direction: str
    type: str
    body: str | None
    status: str | None
    created_at: datetime
