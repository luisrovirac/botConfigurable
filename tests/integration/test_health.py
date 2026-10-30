from fastapi import FastAPI
from httpx import AsyncClient

from core.db import create_engine, create_session_factory


async def test_healthz(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.json() == {"status": "ok"}


async def test_readyz_checks_the_database(client: AsyncClient) -> None:
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


async def test_readyz_reports_unavailable_database(app: FastAPI, client: AsyncClient) -> None:
    healthy = app.state.session_factory
    broken = create_engine("postgresql+asyncpg://nadie:x@127.0.0.1:1/nada")
    app.state.session_factory = create_session_factory(broken)
    try:
        response = await client.get("/readyz")
    finally:
        app.state.session_factory = healthy
        await broken.dispose()
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["database"].startswith("error")


async def test_metrics_are_exposed(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "webhook_requests_total" in response.text
