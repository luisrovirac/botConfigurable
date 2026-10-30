"""Motor de flujos (maquina de estados). No envia nada: devuelve respuestas y el nodo actual."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from flows.definition import FlowDefinition, NodeDefinition

_DOUBLE_SPACES = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"[ \t]+([,.;:!?])")


class FlowError(Exception):
    """El flujo no se puede ejecutar (definicion inconsistente o ciclo sin espera)."""


@dataclass(frozen=True)
class FlowContext:
    """Datos de la conversacion disponibles en los textos, p. ej. {nombre}."""

    variables: Mapping[str, str] = field(default_factory=dict)

    def render(self, template: str) -> str:
        rendered = template.format_map(_KeepUnknown(self.variables))
        # Una variable vacia no debe dejar "Hola ," ni espacios dobles.
        return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", _DOUBLE_SPACES.sub(" ", rendered))


@dataclass(frozen=True)
class Step:
    replies: list[str]
    next_node: str | None
    waits: bool = False


@dataclass(frozen=True)
class FlowOutcome:
    replies: list[str]
    current_node: str


class NodeHandler(Protocol):
    """Comportamiento de un tipo de nodo (Strategy). Se registran por `type`."""

    def enter(self, node: NodeDefinition, context: FlowContext) -> Step: ...

    def receive(self, node: NodeDefinition, text: str, context: FlowContext) -> Step: ...


class FlowEngine:
    def __init__(self, handlers: Mapping[str, NodeHandler], max_steps: int = 20) -> None:
        self._handlers = handlers
        self._max_steps = max_steps

    def start(self, flow: FlowDefinition, context: FlowContext) -> FlowOutcome:
        return self._enter(flow, flow.start, [], context)

    def advance(
        self, flow: FlowDefinition, current_node: str, text: str, context: FlowContext
    ) -> FlowOutcome:
        """Procesa lo que escribio el usuario estando en `current_node`."""
        if current_node not in flow.nodes:
            # El flujo cambio de version y el nodo ya no existe: se empieza de nuevo.
            return self.start(flow, context)
        node = flow.nodes[current_node]
        step = self._handler(node).receive(node, text, context)
        if step.next_node is None:
            return FlowOutcome(step.replies, current_node)
        return self._enter(flow, step.next_node, step.replies, context)

    def _enter(
        self, flow: FlowDefinition, node_id: str, replies: list[str], context: FlowContext
    ) -> FlowOutcome:
        collected = list(replies)
        for _ in range(self._max_steps):
            node = flow.nodes[node_id]
            step = self._handler(node).enter(node, context)
            collected.extend(step.replies)
            if step.waits:
                return FlowOutcome(collected, node_id)
            if step.next_node is None:
                return FlowOutcome(collected, flow.start)
            node_id = step.next_node
        raise FlowError(f"El flujo {flow.key} no se detiene en {self._max_steps} pasos")

    def _handler(self, node: NodeDefinition) -> NodeHandler:
        try:
            return self._handlers[node.type]
        except KeyError as exc:
            raise FlowError(f"No hay handler para nodos de tipo '{node.type}'") from exc


class _KeepUnknown(dict[str, str]):
    """Deja {variable} tal cual si no hay valor, en lugar de fallar."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
