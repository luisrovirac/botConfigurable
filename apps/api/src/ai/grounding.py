from core.types import JSONDict


class GroundingGate:
    """Verifica que IDs, precios y fechas de la respuesta existan en tool_results."""

    def check(self, response: JSONDict, tool_results: JSONDict) -> bool:
        raise NotImplementedError("Pendiente: Fase 2 (docs/05-plan-mejoras.md)")
