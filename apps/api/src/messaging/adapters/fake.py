from dataclasses import dataclass, field
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SentMessage:
    sender_id: str
    to: str
    text: str
    provider_message_id: str


@dataclass
class FakeChannelAdapter:
    """No llama a ningun proveedor: registra el envio. Para desarrollo sin credenciales y tests.

    Se activa con WHATSAPP_SEND_MODE=fake.
    """

    sent: list[SentMessage] = field(default_factory=list)

    async def send_text(self, sender_id: str, to: str, text: str) -> str:
        message = SentMessage(sender_id, to, text, f"fake.{uuid4().hex}")
        self.sent.append(message)
        logger.info("fake_message_sent", to=to, text=text, id=message.provider_message_id)
        return message.provider_message_id

    def capabilities(self) -> dict[str, bool]:
        return {"templates": False, "buttons": False, "window_24h": True, "media": False}
