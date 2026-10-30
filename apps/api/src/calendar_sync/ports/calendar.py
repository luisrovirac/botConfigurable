from datetime import datetime
from typing import Protocol


class CalendarAdapter(Protocol):
    """Calendario externo (Google, Microsoft) para sincronizar citas."""

    async def create_event(self, title: str, starts_at: datetime, ends_at: datetime) -> str:
        """Crea el evento y devuelve su id externo."""
        ...
