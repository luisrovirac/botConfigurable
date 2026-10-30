class InstagramAdapter:
    """Instagram Messaging API."""

    async def send_text(self, sender_id: str, to: str, text: str) -> str:
        raise NotImplementedError("Pendiente: Fase 1 (docs/05-plan-mejoras.md)")

    def capabilities(self) -> dict[str, bool]:
        return {"templates": False, "buttons": False, "window_24h": False, "media": True}
