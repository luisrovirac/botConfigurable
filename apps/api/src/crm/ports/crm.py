from typing import Protocol


class CRMAdapter(Protocol):
    async def upsert_contact(self, **kwargs) -> str:
        ...
