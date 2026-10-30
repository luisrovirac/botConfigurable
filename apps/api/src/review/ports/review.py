from typing import Protocol


class ReviewAdapter(Protocol):
    """Plataforma de resenas (Google Business Profile...)."""

    async def get_review_link(self, location_id: str) -> str: ...
