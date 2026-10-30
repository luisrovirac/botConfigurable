from core.types import JSONDict


class AnthropicAdapter:
    """Claude via la API de Anthropic."""

    async def complete(
        self, messages: list[JSONDict], tools: list[JSONDict] | None = None
    ) -> JSONDict:
        raise NotImplementedError("Pendiente: Fase 2 (docs/05-plan-mejoras.md)")
