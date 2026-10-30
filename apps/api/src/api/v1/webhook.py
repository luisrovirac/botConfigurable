import json
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, get_settings_dep, get_webhook_ingestor
from core.config import Settings
from core.metrics import WEBHOOK_REQUESTS
from core.security import constant_time_equals, verify_signature
from messaging.webhook_ingest import WebhookIngestor
from messaging.whatsapp_payload import WebhookPayload

router = APIRouter(prefix="/webhook", tags=["webhooks"])
logger = structlog.get_logger(__name__)

_CHANNEL = "whatsapp"


@router.get("/whatsapp", response_class=PlainTextResponse)
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


@router.post("/whatsapp")
async def receive_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    session: Annotated[AsyncSession, Depends(get_session)],
    ingestor: Annotated[WebhookIngestor, Depends(get_webhook_ingestor)],
) -> dict[str, str]:
    """Guarda lo recibido y responde 200 enseguida; el worker procesa despues."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(settings.whatsapp_app_secret, body, signature):
        WEBHOOK_REQUESTS.labels(channel=_CHANNEL, status="invalid_signature").inc()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    result = await ingestor.ingest(session, _parse_payload(body))
    if result.unknown_channels:
        # Se responde 200 igual: si no, Meta reintenta un mensaje que nunca se podra asignar.
        logger.warning("webhook_unknown_channel", phone_number_ids=sorted(result.unknown_channels))
        WEBHOOK_REQUESTS.labels(channel=_CHANNEL, status="unknown_channel").inc()
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
