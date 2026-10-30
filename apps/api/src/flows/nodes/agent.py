from flows.engine.fsm import FlowState, Node


class AgentNode(Node):
    async def run(self, state: FlowState) -> FlowState:
        state.node = "end"
        return state
