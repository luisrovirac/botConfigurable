from typing import Protocol


class ReviewAdapter(Protocol):
    async def get_review_link(self, **kwargs) -> str:
        ...
