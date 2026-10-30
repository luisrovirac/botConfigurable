from dataclasses import dataclass
from typing import Any


@dataclass
class OutboxMessage:
    id: str
    tenant_id: str
    conversation_id: str
    payload: dict[str, Any]
    status: str
    idempotency_key: str
    attempts: int = 0
    blocked_reason: str | None = None
