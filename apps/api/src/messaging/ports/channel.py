from typing import Protocol


class ChannelAdapter(Protocol):
    """Envia mensajes por un canal (WhatsApp, Instagram, Telegram...)."""

    async def send_text(self, to: str, text: str) -> str:
        """Envia un texto y devuelve el id del mensaje en el proveedor."""
        ...

    def capabilities(self) -> dict[str, bool]: ...
