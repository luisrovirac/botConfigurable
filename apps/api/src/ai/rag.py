from core.types import JSONDict


class RAG:
    """Recuperacion hibrida sobre la base de conocimiento del inquilino."""

    async def retrieve(self, query: str, tenant_id: str) -> list[JSONDict]:
        raise NotImplementedError("Pendiente: Fase 2 (docs/05-plan-mejoras.md)")
