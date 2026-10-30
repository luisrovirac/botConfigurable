class InstagramAdapter:
    async def send_text(self, to: str, text: str, **kwargs) -> str:
        return "ig_123"

    def capabilities(self) -> dict[str, bool]:
        return {"templates": False, "buttons": False, "window_24h": False, "media": True}
