from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from flows.models import FlowInstance


class FlowInstanceStore:
    """Guarda en que nodo del flujo esta cada conversacion (tabla flow_instance)."""

    async def current_node(self, session: AsyncSession, conversation_id: UUID) -> str | None:
        node: str | None = await session.scalar(
            select(FlowInstance.current_node).where(FlowInstance.conversation_id == conversation_id)
        )
        return node

    async def save(
        self,
        session: AsyncSession,
        tenant_id: str,
        conversation_id: UUID,
        flow_key: str,
        current_node: str,
    ) -> None:
        values = insert(FlowInstance).values(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            pack_version=flow_key,
            current_node=current_node,
        )
        await session.execute(
            values.on_conflict_do_update(
                constraint="uq_flow_instance_conversation",
                set_={
                    "pack_version": values.excluded.pack_version,
                    "current_node": values.excluded.current_node,
                },
            )
        )
