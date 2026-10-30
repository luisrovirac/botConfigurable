from fastapi import FastAPI
from httpx import AsyncClient
from redis.asyncio import Redis


async def test_healthz(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.json() == {"status": "ok"}


async def test_readyz_checks_database_and_redis(client: AsyncClient) -> None:
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok", "redis": "ok"}


async def test_readyz_reports_unavailable_redis(app: FastAPI, client: AsyncClient) -> None:
    healthy = app.state.redis
    app.state.redis = Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2)
    try:
        response = await client.get("/readyz")
    finally:
        await app.state.redis.aclose()
        app.state.redis = healthy
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["redis"].startswith("error")


async def test_metrics_are_exposed(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "webhook_requests_total" in response.text


async def test_login_is_explicitly_not_implemented(client: AsyncClient) -> None:
    response = await client.post("/auth/login")
    assert response.status_code == 501
