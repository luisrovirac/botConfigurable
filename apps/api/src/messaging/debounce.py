import asyncio
from collections import defaultdict
from datetime import datetime, timedelta


class Debouncer:
    def __init__(self, delay_seconds: float = 2.5) -> None:
        self.delay_seconds = delay_seconds
        self._buffers: dict[str, list[str]] = defaultdict(list)
        self._tasks: dict[str, asyncio.Task] = {}

    async def add(self, conversation_id: str, message: str, callback) -> None:
        self._buffers[conversation_id].append(message)
        if conversation_id in self._tasks:
            self._tasks[conversation_id].cancel()
        self._tasks[conversation_id] = asyncio.create_task(self._flush_after(conversation_id, callback))

    async def _flush_after(self, conversation_id: str, callback) -> None:
        await asyncio.sleep(self.delay_seconds)
        messages = self._buffers.pop(conversation_id, [])
        self._tasks.pop(conversation_id, None)
        if messages:
            await callback(conversation_id, messages)
