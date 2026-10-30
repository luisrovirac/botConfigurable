import json

import httpx
import pytest
import respx

from messaging.adapters.whatsapp_cloud import WhatsAppCloudAdapter
from messaging.ports.channel import PermanentSendError, TransientSendError

URL = "https://graph.test/v21.0/PHONE_ID/messages"


def _adapter(client: httpx.AsyncClient) -> WhatsAppCloudAdapter:
    return WhatsAppCloudAdapter(
        client, base_url="https://graph.test/", api_version="v21.0", access_token="token"
    )


@pytest.fixture(autouse=True)
def no_backoff_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    # Los reintentos esperan con backoff; en los tests no hace falta esperar.
    async def instant(_: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", instant)


@respx.mock
async def test_sends_text_and_returns_provider_id() -> None:
    route = respx.post(URL).respond(200, json={"messages": [{"id": "wamid.ok"}]})
    async with httpx.AsyncClient() as client:
        provider_id = await _adapter(client).send_text("PHONE_ID", "521555", "Hola")

    assert provider_id == "wamid.ok"
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer token"
    assert json.loads(request.content)["text"]["body"] == "Hola"


@respx.mock
async def test_retries_transient_errors_then_succeeds() -> None:
    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(503),
            httpx.ConnectError("caida"),
            httpx.Response(200, json={"messages": [{"id": "wamid.ok"}]}),
        ]
    )
    async with httpx.AsyncClient() as client:
        assert await _adapter(client).send_text("PHONE_ID", "521555", "Hola") == "wamid.ok"
    assert route.call_count == 3


@respx.mock
async def test_persistent_transient_error_is_reported_as_transient() -> None:
    respx.post(URL).respond(429)
    async with httpx.AsyncClient() as client:
        with pytest.raises(TransientSendError):
            await _adapter(client).send_text("PHONE_ID", "521555", "Hola")


@respx.mock
@pytest.mark.parametrize(
    "response",
    [httpx.Response(400, json={"error": "numero invalido"}), httpx.Response(200, json={})],
)
async def test_client_errors_and_bad_responses_are_permanent(response: httpx.Response) -> None:
    route = respx.post(URL).mock(return_value=response)
    async with httpx.AsyncClient() as client:
        with pytest.raises(PermanentSendError):
            await _adapter(client).send_text("PHONE_ID", "521555", "Hola")
    assert route.call_count == 1
