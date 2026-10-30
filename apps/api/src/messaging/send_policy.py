from dataclasses import dataclass
from typing import Protocol

from core.types import JSONDict


@dataclass(frozen=True)
class SendDecision:
    allowed: bool
    reason: str | None = None


class SendPolicy(Protocol):
    """Decide si un mensaje saliente puede enviarse (ventana 24 h, consentimiento, etc.)."""

    def evaluate(self, tenant_id: str, conversation_id: str, payload: JSONDict) -> SendDecision: ...


class AllowAllPolicy:
    """Politica provisional: permite todo.

    La Etapa 2 la reemplaza por reglas reales (supresion -> blocked_consent,
    ventana de 24 h cerrada -> blocked_window). Ver docs/05-plan-mejoras.md 2.5.
    """

    def evaluate(self, tenant_id: str, conversation_id: str, payload: JSONDict) -> SendDecision:
        return SendDecision(allowed=True)
