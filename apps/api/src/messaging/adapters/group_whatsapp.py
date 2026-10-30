class WhatsAppGroupsAdapter:
    async def send_text(self, to: str, text: str, **kwargs) -> str:
        return "grp_123"

    def capabilities(self) -> dict[str, bool]:
        return {"templates": True, "group": True, "recipient_type": True}
