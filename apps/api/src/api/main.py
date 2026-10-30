from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.v1 import appointments, auth, campaigns, catalog, inbox, leads, packs, webhook
from core.config import get_settings
from core.db import init_db
from core.logging import configure_logging

app = FastAPI(title="botConfigurable", version="0.1.0")


@app.on_event("startup")
async def startup() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db(settings.database_url)


app.include_router(webhook.router)
app.include_router(inbox.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(appointments.router)
app.include_router(leads.router)
app.include_router(campaigns.router)
app.include_router(packs.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/metrics")
async def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)







