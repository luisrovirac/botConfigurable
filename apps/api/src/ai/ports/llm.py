from typing import Protocol

from core.types import JSONDict


class LLMProvider(Protocol):
    """Proveedor de modelo de lenguaje (Anthropic, Ollama...)."""

    async def complete(
        self, messages: list[JSONDict], tools: list[JSONDict] | None = None
    ) -> JSONDict: ...
