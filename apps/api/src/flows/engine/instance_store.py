from flows.engine.fsm import FlowState


class FlowInstanceStore:
    """Persistencia del estado del flujo en flow_instance."""

    async def save(self, state: FlowState) -> None:
        raise NotImplementedError("Pendiente: Etapa 2, punto 2.4 (docs/05-plan-mejoras.md)")
