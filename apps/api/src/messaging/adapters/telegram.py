class TelegramAdapter:
    """Telegram Bot API."""

    async def send_text(self, to: str, text: str) -> str:
        raise NotImplementedError("Pendiente: Fase 7 (docs/05-plan-mejoras.md)")

    def capabilities(self) -> dict[str, bool]:
        return {"groups": True}
