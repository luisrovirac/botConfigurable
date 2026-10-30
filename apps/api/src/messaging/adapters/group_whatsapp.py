class WhatsAppGroupsAdapter:
    """Grupos de WhatsApp (OBA)."""

    async def send_text(self, sender_id: str, to: str, text: str) -> str:
        raise NotImplementedError("Pendiente: Fase 7 (docs/05-plan-mejoras.md)")

    def capabilities(self) -> dict[str, bool]:
        return {"templates": True, "group": True, "recipient_type": True}
