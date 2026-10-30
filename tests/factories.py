"""Constructores de datos de prueba."""

import hashlib
import hmac
import json

from core.types import JSONDict

TEST_APP_SECRET = "test-app-secret"
TEST_VERIFY_TOKEN = "test-verify-token"


def whatsapp_text_payload(
    message_id: str, sender: str = "5215550000001", body: str = "Hola", name: str | None = "Ana"
) -> JSONDict:
    """Payload minimo de un mensaje de texto entrante, como lo envia Meta."""
    contacts = [{"wa_id": sender, "profile": {"name": name}}] if name else []
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "PHONE_ID"},
                            "contacts": contacts,
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": sender,
                                    "timestamp": "1730000000",
                                    "type": "text",
                                    "text": {"body": body},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def signature_headers(body: bytes, app_secret: str) -> dict[str, str]:
    """Cabeceras con la firma que pone Meta (X-Hub-Signature-256) sobre el cuerpo crudo."""
    digest = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"}


def signed(payload: JSONDict, app_secret: str) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload).encode()
    return body, signature_headers(body, app_secret)
