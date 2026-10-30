"""Una vuelta del worker: para cada inquilino con trabajo, procesa entradas y envia salidas."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.tenant import set_tenant
from core.tenant_directory import TenantDirectory
from messaging.inbound_processor import InboundProcessor
from messaging.outbox_sender import OutboxSender


class WorkerCycle:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        directory: TenantDirectory,
        inbound: InboundProcessor,
        outbox: OutboxSender,
    ) -> None:
        self._sessions = session_factory
        self._directory = directory
        self._inbound = inbound
        self._outbox = outbox

    async def run_once(self) -> int:
        """Devuelve cuantos elementos proceso; 0 significa que no habia trabajo."""
        async with self._sessions() as session, session.begin():
            tenants = await self._directory.tenants_with_pending_work(session)
        processed = 0
        for tenant_id in tenants:
            # Transacciones separadas: las respuestas encoladas al procesar la entrada
            # quedan confirmadas antes de que el sender las tome.
            async with self._sessions() as session, session.begin():
                await set_tenant(session, tenant_id)
                processed += await self._inbound.process_due(session, tenant_id)
            async with self._sessions() as session, session.begin():
                await set_tenant(session, tenant_id)
                processed += await self._outbox.send_due(session, tenant_id)
        return processed
