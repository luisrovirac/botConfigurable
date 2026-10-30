"""Payload del webhook de WhatsApp Cloud API (solo los campos que usa la app).

Los modelos aceptan campos extra para no romperse cuando Meta agrega datos, y los conservan
al volcarlos (se guardan crudos en webhook_event y message_status_event).
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


class WhatsAppStatus(_MetaModel):
    id: str
    status: str  # sent, delivered, read, failed


class WhatsAppProfile(_MetaModel):
    name: str | None = None


class WhatsAppContact(_MetaModel):
    wa_id: str
    profile: WhatsAppProfile | None = None


class Metadata(_MetaModel):
    phone_number_id: str | None = None


class ChangeValue(_MetaModel):
    metadata: Metadata = Metadata()
    messages: list[WhatsAppMessage] = []
    statuses: list[WhatsAppStatus] = []
    contacts: list[WhatsAppContact] = []


class Change(_MetaModel):
    field: str = ""
    value: ChangeValue = ChangeValue()


class Entry(_MetaModel):
    changes: list[Change] = []


@dataclass(frozen=True)
class InboundMessage:
    phone_number_id: str | None
    provider_message_id: str
    sender_phone: str
    sender_name: str | None
    type: str
    body: str | None
    raw: JSONDict


@dataclass(frozen=True)
class StatusUpdate:
    phone_number_id: str | None
    provider_message_id: str
    status: str
    raw: JSONDict


class WebhookPayload(_MetaModel):
    entry: list[Entry] = []

    def _values(self) -> Iterator[ChangeValue]:
        for entry in self.entry:
            for change in entry.changes:
                yield change.value

    def inbound_messages(self) -> Iterator[InboundMessage]:
        """Todos los mensajes del lote (Meta puede agrupar varios en un solo POST)."""
        for value in self._values():
            names = {c.wa_id: c.profile.name if c.profile else None for c in value.contacts}
            for message in value.messages:
                yield InboundMessage(
                    phone_number_id=value.metadata.phone_number_id,
                    provider_message_id=message.id,
                    sender_phone=message.from_,
                    sender_name=names.get(message.from_),
                    type=message.type,
                    body=message.text.body if message.text else None,
                    raw=message.model_dump(mode="json", by_alias=True)
                    | {"profile_name": names.get(message.from_)},
                )

    def status_updates(self) -> Iterator[StatusUpdate]:
        for value in self._values():
            for status in value.statuses:
                yield StatusUpdate(
                    phone_number_id=value.metadata.phone_number_id,
                    provider_message_id=status.id,
                    status=status.status,
                    raw=status.model_dump(mode="json", by_alias=True),
                )
