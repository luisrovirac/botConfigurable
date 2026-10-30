class CampaignDispatcher:
    """Envio de campanas por lotes respetando consentimiento y topes."""

    async def dispatch_batch(self, campaign_id: str, batch_size: int = 100) -> int:
        raise NotImplementedError("Pendiente: Fase 6 (docs/05-plan-mejoras.md)")
