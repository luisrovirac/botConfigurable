from core.types import JSONDict


class GroupHandler:
    """Reglas del bot dentro de grupos."""

    async def handle(self, group_id: str, message: JSONDict) -> None:
        raise NotImplementedError("Pendiente: Fase 7 (docs/05-plan-mejoras.md)")
