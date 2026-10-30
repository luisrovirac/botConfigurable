from datetime import datetime


class GoogleCalendarAdapter:
    """Google Calendar."""

    async def create_event(self, title: str, starts_at: datetime, ends_at: datetime) -> str:
        raise NotImplementedError("Pendiente: Fase 4 (docs/05-plan-mejoras.md)")
