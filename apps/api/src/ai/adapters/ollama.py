class OllamaAdapter:
    async def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        return {"content": "", "tool_calls": []}
