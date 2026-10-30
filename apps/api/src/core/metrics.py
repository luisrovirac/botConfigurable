from prometheus_client import Counter, Histogram

WEBHOOK_REQUESTS = Counter("webhook_requests_total", "Webhook requests", ["channel", "status"])
OUTBOX_PROCESSED = Counter("outbox_processed_total", "Outbox processed", ["status"])
LLM_CALLS = Counter("llm_calls_total", "LLM calls", ["provider", "model"])
LLM_LATENCY = Histogram("llm_latency_seconds", "LLM latency", ["provider"])
