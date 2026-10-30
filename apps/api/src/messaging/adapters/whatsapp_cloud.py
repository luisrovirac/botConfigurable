from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from messaging.ports.channel import PermanentSendError, TransientSendError

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class WhatsAppCloudAdapter:
    """WhatsApp Cloud API (Graph API de Meta).

    Reintenta con backoff exponencial los fallos temporales dentro del mismo envio; si
    persisten, lanza TransientSendError y el worker reprograma el mensaje.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        api_version: str,
        access_token: str,
        max_attempts: int = 3,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._api_version = api_version
        self._access_token = access_token
        self._max_attempts = max_attempts

    async def send_text(self, sender_id: str, to: str, text: str) -> str:
        url = f"{self._base_url}/{self._api_version}/{sender_id}/messages"
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(TransientSendError),
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=0.5, max=8),
            reraise=True,
        ):
            with attempt:
                return _message_id(await self._post(url, body))
        raise AssertionError("AsyncRetrying termina devolviendo o lanzando")  # pragma: no cover

    def capabilities(self) -> dict[str, bool]:
        return {"templates": True, "buttons": True, "window_24h": True, "media": True}

    async def _post(self, url: str, body: dict[str, Any]) -> httpx.Response:
        try:
            response = await self._client.post(
                url, json=body, headers={"Authorization": f"Bearer {self._access_token}"}
            )
        except httpx.TransportError as exc:
            raise TransientSendError(f"Error de red con Meta: {exc}") from exc
        if response.status_code in _RETRYABLE_STATUS:
            raise TransientSendError(f"Meta respondio {response.status_code}: {response.text}")
        if response.is_error:
            raise PermanentSendError(f"Meta respondio {response.status_code}: {response.text}")
        return response


def _message_id(response: httpx.Response) -> str:
    try:
        message_id = response.json()["messages"][0]["id"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise PermanentSendError(f"Respuesta inesperada de Meta: {response.text}") from exc
    return str(message_id)
