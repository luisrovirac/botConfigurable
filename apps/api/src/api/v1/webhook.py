from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from uuid import uuid4

from core.config import get_settings
from core.db import SessionLocal
from core.security import verify_signature
from core.tenant import set_tenant
from messaging.inbound_pipeline import InboundPipeline
from messaging.models import OutboxMessage

router = APIRouter()
pipeline = InboundPipeline()


@router.get("/webhook/whatsapp")
async def verify_webhook(
    request: Request, hub_mode: str = "", hub_verify_token: str = "", hub_challenge: str = ""
) -> PlainTextResponse:
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request) -> dict[str, str]:
    settings = get_settings()
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if settings.whatsapp_app_secret and not verify_signature(settings.whatsapp_app_secret, body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    import json

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # TODO: obtener tenant_id desde channel_account
    tenant_id = "demo"
    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="DB not initialized")
    async with SessionLocal() as session:
        await set_tenant(session, tenant_id)
        await pipeline.process(session, tenant_id, payload)
        # Encolar respuesta dummy con idempotencia
        outbox = OutboxMessage(
            tenant_id=tenant_id,
            conversation_id=uuid4(),
            payload={"type": "text", "body": "Hola"},
            status="pending",
            idempotency_key=str(uuid4()),
        )
        session.add(outbox)
        await session.commit()
    return {"status": "ok"}
