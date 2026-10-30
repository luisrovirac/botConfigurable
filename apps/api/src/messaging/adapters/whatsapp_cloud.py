class WhatsAppCloudAdapter:
    """WhatsApp Cloud API (Graph API de Meta)."""

    async def send_text(self, to: str, text: str) -> str:
        raise NotImplementedError("Pendiente: Etapa 2, punto 2.6 (docs/05-plan-mejoras.md)")

    def capabilities(self) -> dict[str, bool]:
        return {"templates": True, "buttons": True, "window_24h": True, "media": True}
