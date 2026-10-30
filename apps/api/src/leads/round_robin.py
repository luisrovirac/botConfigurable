class RoundRobin:
    """Reparto equitativo de leads con cursor persistido."""

    async def assign(self, tenant_id: str, agents: list[str]) -> str | None:
        raise NotImplementedError("Pendiente: Fase 5 (docs/05-plan-mejoras.md)")
