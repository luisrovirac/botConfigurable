from flows.engine.fsm import FlowState


class AgentNode:
    """Nodo que delega en el agente LLM con herramientas permitidas."""

    async def run(self, state: FlowState) -> FlowState:
        raise NotImplementedError("Pendiente: Fase 2 (docs/05-plan-mejoras.md)")
