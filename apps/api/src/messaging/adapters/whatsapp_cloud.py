class WhatsAppCloudAdapter:
    async def send_text(self, to: str, text: str, **kwargs) -> str:
        return "msg_123"

    def capabilities(self) -> dict[str, bool]:
        return {"templates": True, "buttons": True, "window_24h": True, "media": True}
