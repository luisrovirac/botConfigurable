from datetime import UTC, datetime, timedelta

import pytest

from consent.service import ConsentIntent, ConsentService
from messaging.send_policy import (
    MessagingWindowRule,
    RuleBasedPolicy,
    SendContext,
    SendDecision,
    SuppressionRule,
)

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)
POLICY = RuleBasedPolicy([SuppressionRule(), MessagingWindowRule(timedelta(hours=24))])


def _context(
    kind: str = "reply", suppressed: bool = False, hours_since_inbound: float | None = 1
) -> SendContext:
    last = None if hours_since_inbound is None else NOW - timedelta(hours=hours_since_inbound)
    return SendContext(kind=kind, suppressed=suppressed, last_inbound_at=last, now=NOW)


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        (_context(), SendDecision(allowed=True)),
        (_context(hours_since_inbound=23.9), SendDecision(allowed=True)),
        (_context(hours_since_inbound=24.1), SendDecision(False, "blocked_window")),
        (_context(hours_since_inbound=None), SendDecision(False, "blocked_window")),
        (_context(suppressed=True), SendDecision(False, "blocked_consent")),
        (_context(kind="opt_out_confirmation", suppressed=True), SendDecision(allowed=True)),
        # La supresion se revisa primero: es la razon mas importante para el inbox.
        (_context(suppressed=True, hours_since_inbound=30), SendDecision(False, "blocked_consent")),
    ],
)
def test_policy_decisions(context: SendContext, expected: SendDecision) -> None:
    assert POLICY.evaluate(context) == expected


CONSENT = ConsentService(frozenset({"BAJA", "STOP"}), frozenset({"ALTA"}))


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("BAJA", ConsentIntent.OPT_OUT),
        (" stop ", ConsentIntent.OPT_OUT),
        ("alta", ConsentIntent.OPT_IN),
        ("quiero darme de baja", None),
        ("", None),
        (None, None),
    ],
)
def test_consent_keywords_must_be_the_whole_message(
    text: str | None, intent: ConsentIntent | None
) -> None:
    assert CONSENT.intent(text) == intent
