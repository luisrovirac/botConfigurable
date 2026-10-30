from dataclasses import dataclass, field
from typing import Protocol

from core.types import JSONDict


@dataclass
class FlowState:
    conversation_id: str
    node: str
    variables: JSONDict = field(default_factory=dict)


class Node(Protocol):
    """Un paso del flujo: recibe el estado y devuelve el siguiente."""

    async def run(self, state: FlowState) -> FlowState: ...
