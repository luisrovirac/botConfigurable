from typing import Protocol


class SendError(Exception):
    """El proveedor no acepto el mensaje."""


class TransientSendError(SendError):
    """Fallo temporal (red, 429, 5xx): conviene reintentar mas tarde."""


class PermanentSendError(SendError):
    """Fallo definitivo (datos invalidos, numero inexistente...): no reintentar."""


class ChannelAdapter(Protocol):
    """Envia mensajes por un canal (WhatsApp, Instagram, Telegram...)."""

    async def send_text(self, sender_id: str, to: str, text: str) -> str:
        """Envia un texto desde la cuenta `sender_id` y devuelve el id del mensaje en el proveedor.

        Lanza TransientSendError o PermanentSendError si el proveedor no lo acepta.
        """
        ...

    def capabilities(self) -> dict[str, bool]: ...
