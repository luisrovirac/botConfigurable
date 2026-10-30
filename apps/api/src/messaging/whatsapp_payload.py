"""Payload del webhook de WhatsApp Cloud API (solo los campos que usa la app).

Los modelos aceptan campos extra para no romperse cuando Meta agrega datos, y los conservan
al volcarlos (se guardan crudos en webhook_event).
"""

from collections.abc import Iterator
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from core.types import JSONDict


class _MetaModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class WhatsAppText(_MetaModel):
    body: str


class WhatsAppMessage(_MetaModel):
    id: str
    from_: str = Field(alias="from")
    type: str
    text: WhatsAppText | None = None


class WhatsAppProfile(_MetaModel):
    name: str | None = None


class WhatsAppContact(_MetaModel):
    wa_id: str
    profile: WhatsAppProfile | None = None


class ChangeValue(_MetaModel):
    messages: list[WhatsAppMessage] = []
    contacts: list[WhatsAppContact] = []


class Change(_MetaModel):
    field: str = ""
    value: ChangeValue = ChangeValue()


class Entry(_MetaModel):
    changes: list[Change] = []


@dataclass(frozen=True)
class InboundMessage:
    provider_message_id: str
    sender_phone: str
    sender_name: str | None
    type: str
    body: str | None
    raw: JSONDict


class WebhookPayload(_MetaModel):
    entry: list[Entry] = []

    def inbound_messages(self) -> Iterator[InboundMessage]:
        """Todos los mensajes del lote (Meta puede agrupar varios en un solo POST)."""
        for entry in self.entry:
            for change in entry.changes:
                names = {
                    c.wa_id: c.profile.name if c.profile else None for c in change.value.contacts
                }
                for message in change.value.messages:
                    yield InboundMessage(
                        provider_message_id=message.id,
                        sender_phone=message.from_,
                        sender_name=names.get(message.from_),
                        type=message.type,
                        body=message.text.body if message.text else None,
                        raw=message.model_dump(mode="json", by_alias=True),
                    )
