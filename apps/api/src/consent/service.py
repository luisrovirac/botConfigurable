"""Consentimiento: altas y bajas por palabra clave (BAJA/STOP, ALTA/START)."""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from consent.models import ConsentEvent, SuppressionList


class ConsentIntent(StrEnum):
    OPT_OUT = "opt-out"
    OPT_IN = "opt-in"


class ConsentService:
    def __init__(self, opt_out_keywords: frozenset[str], opt_in_keywords: frozenset[str]) -> None:
        self._keywords = {
            **dict.fromkeys(opt_out_keywords, ConsentIntent.OPT_OUT),
            **dict.fromkeys(opt_in_keywords, ConsentIntent.OPT_IN),
        }

    def intent(self, text: str | None) -> ConsentIntent | None:
        """El mensaje completo debe ser la palabra clave (sin importar mayusculas)."""
        return self._keywords.get((text or "").strip().upper())

    async def record(
        self,
        session: AsyncSession,
        tenant_id: str,
        contact_id: UUID,
        phone: str,
        intent: ConsentIntent,
        text_exact: str,
    ) -> None:
        """Registra el evento (con el texto exacto) y actualiza la lista de supresion."""
        session.add(
            ConsentEvent(
                tenant_id=tenant_id,
                contact_id=contact_id,
                channel="whatsapp",
                source="keyword",
                text_exact=text_exact,
                action=intent.value,
            )
        )
        if intent is ConsentIntent.OPT_OUT:
            await session.execute(
                insert(SuppressionList)
                .values(tenant_id=tenant_id, phone=phone, reason="opt-out")
                .on_conflict_do_nothing(constraint="uq_suppression_tenant_phone")
            )
        else:
            await session.execute(delete(SuppressionList).where(SuppressionList.phone == phone))
        await session.flush()
