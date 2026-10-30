from flows.engine.fsm import FlowState, Node


class AnswerNode(Node):
    async def run(self, state: FlowState) -> FlowState:
        return state
