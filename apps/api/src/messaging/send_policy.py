from dataclasses import dataclass


@dataclass
class SendDecision:
    allowed: bool
    reason: str | None = None


class SendPolicy:
    def evaluate(self, tenant_id: str, conversation_id: str, payload: dict) -> SendDecision:
        # 24h window, templates, consent, quiet hours, marketing limits
        if payload.get("blocked"):
            return SendDecision(allowed=False, reason="blocked_window")
        return SendDecision(allowed=True)
