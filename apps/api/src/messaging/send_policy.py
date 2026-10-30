"""Politica de envio: decide si un mensaje saliente puede salir (ver plan 2.5)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

# Tipos de mensaje que salen aunque el contacto este en la lista de supresion.
CONSENT_EXEMPT_KINDS = frozenset({"opt_out_confirmation"})


@dataclass(frozen=True)
class SendDecision:
    allowed: bool
    reason: str | None = None


ALLOWED = SendDecision(allowed=True)


@dataclass(frozen=True)
class SendContext:
    kind: str  # reply, opt_out_confirmation, opt_in_confirmation...
    suppressed: bool  # el contacto pidio no recibir mensajes
    last_inbound_at: datetime | None  # ultimo mensaje del contacto (abre la ventana de 24 h)
    now: datetime


class SendRule(Protocol):
    def check(self, context: SendContext) -> SendDecision | None:
        """Devuelve una decision de bloqueo, o None si la regla no objeta."""
        ...


class SuppressionRule:
    def check(self, context: SendContext) -> SendDecision | None:
        if context.suppressed and context.kind not in CONSENT_EXEMPT_KINDS:
            return SendDecision(allowed=False, reason="blocked_consent")
        return None


class MessagingWindowRule:
    """Fuera de la ventana de servicio solo se puede escribir con plantillas aprobadas.

    Las plantillas llegan en la Fase 6; hasta entonces, fuera de la ventana se bloquea.
    """

    def __init__(self, window: timedelta) -> None:
        self._window = window

    def check(self, context: SendContext) -> SendDecision | None:
        last = context.last_inbound_at
        if last is None or context.now - last > self._window:
            return SendDecision(allowed=False, reason="blocked_window")
        return None


class SendPolicy(Protocol):
    def evaluate(self, context: SendContext) -> SendDecision: ...


class RuleBasedPolicy:
    """Aplica las reglas en orden; la primera que bloquea decide."""

    def __init__(self, rules: Sequence[SendRule]) -> None:
        self._rules = tuple(rules)

    def evaluate(self, context: SendContext) -> SendDecision:
        for rule in self._rules:
            decision = rule.check(context)
            if decision is not None:
                return decision
        return ALLOWED
