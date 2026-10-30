from flows.definition import MenuNode, NodeDefinition
from flows.engine.fsm import FlowContext, FlowError, Step


class MenuHandler:
    """Muestra las opciones y espera; con una opcion valida sigue a su nodo destino."""

    def enter(self, node: NodeDefinition, context: FlowContext) -> Step:
        menu = _as_menu(node)
        return Step(replies=[context.render(menu.text)], next_node=None, waits=True)

    def receive(self, node: NodeDefinition, text: str, context: FlowContext) -> Step:
        menu = _as_menu(node)
        choice = text.strip().lower()
        for option, target in menu.options.items():
            if option.lower() == choice:
                return Step(replies=[], next_node=target)
        replies = [context.render(menu.invalid_text), context.render(menu.text)]
        return Step(replies=replies, next_node=None, waits=True)


def _as_menu(node: NodeDefinition) -> MenuNode:
    if not isinstance(node, MenuNode):
        raise FlowError(f"Se esperaba un nodo 'menu', llego '{node.type}'")
    return node
