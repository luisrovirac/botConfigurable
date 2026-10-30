from typing import Protocol


class ChannelAdapter(Protocol):
    async def send_text(self, to: str, text: str, **kwargs) -> str:
        ...

    def capabilities(self) -> dict[str, bool]:
        ...
