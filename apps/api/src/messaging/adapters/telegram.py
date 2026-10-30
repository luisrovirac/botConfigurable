class TelegramAdapter:
    async def send_text(self, to: str, text: str, **kwargs) -> str:
        return "tg_123"

    def capabilities(self) -> dict[str, bool]:
        return {"groups": True}
