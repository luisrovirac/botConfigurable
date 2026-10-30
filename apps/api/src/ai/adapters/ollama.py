from core.types import JSONDict


class OllamaAdapter:
    """Modelos locales via Ollama."""

    async def complete(
        self, messages: list[JSONDict], tools: list[JSONDict] | None = None
    ) -> JSONDict:
        raise NotImplementedError("Pendiente: Fase 2 (docs/05-plan-mejoras.md)")
