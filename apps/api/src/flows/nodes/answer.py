from flows.definition import AnswerNode, NodeDefinition
from flows.engine.fsm import FlowContext, FlowError, Step


class AnswerHandler:
    """Responde el texto del nodo y sigue al siguiente sin esperar al usuario."""

    def enter(self, node: NodeDefinition, context: FlowContext) -> Step:
        answer = _as_answer(node)
        return Step(replies=[context.render(answer.text)], next_node=answer.next)

    def receive(self, node: NodeDefinition, text: str, context: FlowContext) -> Step:
        raise FlowError("Un nodo 'answer' no espera respuesta del usuario")


def _as_answer(node: NodeDefinition) -> AnswerNode:
    if not isinstance(node, AnswerNode):
        raise FlowError(f"Se esperaba un nodo 'answer', llego '{node.type}'")
    return node
