from flows.engine.fsm import FlowState


class AnswerNode:
    """Nodo que responde un texto fijo segun la opcion elegida."""

    async def run(self, state: FlowState) -> FlowState:
        raise NotImplementedError("Pendiente: Etapa 2, punto 2.4 (docs/05-plan-mejoras.md)")
