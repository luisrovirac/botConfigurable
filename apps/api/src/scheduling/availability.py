from datetime import datetime


class AvailabilityService:
    """Disponibilidad de un recurso segun reglas, ausencias y citas."""

    async def is_available(self, resource_id: str, start: datetime, end: datetime) -> bool:
        raise NotImplementedError("Pendiente: Fase 4 (docs/05-plan-mejoras.md)")
