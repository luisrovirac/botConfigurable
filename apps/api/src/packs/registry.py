class PackRegistry:
    """Publicacion de versiones de packs (borrador, validado, publicado)."""

    async def publish(self, tenant_id: str, pack_id: str, version: str) -> None:
        raise NotImplementedError("Pendiente: Fase 2 (docs/05-plan-mejoras.md)")
