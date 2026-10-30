from typing import Protocol


class CalendarAdapter(Protocol):
    async def create_event(self, **kwargs) -> str:
        ...
