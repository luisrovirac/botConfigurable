from dataclasses import dataclass
from typing import Protocol


@dataclass
class FlowState:
    conversation_id: str
    node: str
    variables: dict


class Node(Protocol):
    async def run(self, state: FlowState) -> FlowState:
        ...
