import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_inbound_pipeline, get_session, get_settings_dep
from core.config import Settings
from core.metrics import WEBHOOK_REQUESTS
from core.security import constant_time_equals, verify_signature
from core.tenant import set_tenant
from messaging.inbound_pipeline import InboundPipeline
from messaging.whatsapp_payload import WebhookPayload

router = APIRouter(tags=["webhooks"])

_CHANNEL = "whatsapp"


@router.get("/webhook/whatsapp", response_class=PlainTextResponse)
async def verify_webhook(
    settings: Annotated[Settings, Depends(get_settings_dep)],
    hub_mode: Annotated[str, Query(alias="hub.mode")] = "",
    hub_verify_token: Annotated[str, Query(alias="hub.verify_token")] = "",
    hub_challenge: Annotated[str, Query(alias="hub.challenge")] = "",
) -> str:
    """Verificacion de la suscripcion que hace Meta al configurar el webhook."""
    if hub_mode == "subscribe" and constant_time_equals(
        hub_verify_token, settings.whatsapp_verify_token
    ):
        return hub_challenge
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def receive_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    session: Annotated[AsyncSession, Depends(get_session)],
    pipeline: Annotated[InboundPipeline, Depends(get_inbound_pipeline)],
) -> dict[str, str]:
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(settings.whatsapp_app_secret, body, signature):
        WEBHOOK_REQUESTS.labels(channel=_CHANNEL, status="invalid_signature").inc()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    payload = _parse_payload(body)
    tenant_id = settings.whatsapp_default_tenant_id  # Etapa 2: resolver por channel_account
    await set_tenant(session, tenant_id)
    await pipeline.process(session, tenant_id, payload)
    WEBHOOK_REQUESTS.labels(channel=_CHANNEL, status="ok").inc()
    return {"status": "ok"}


def _parse_payload(body: bytes) -> WebhookPayload:
    try:
        return WebhookPayload.model_validate(json.loads(body))
    except (json.JSONDecodeError, ValidationError) as exc:
        WEBHOOK_REQUESTS.labels(channel=_CHANNEL, status="invalid_payload").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
        ) from exc
