"""Simulador de WhatsApp: envia a la API webhooks firmados igual que Meta.

Sirve para probar el flujo completo sin credenciales de Meta. Uso (scripts\\simulate.bat):
    simulate "Hola"                      mensaje de texto de un cliente
    simulate "1" --from 5215550002222    otro cliente
    simulate "Hola" --id wamid.X --repeat 2   reenvio del mismo mensaje (no debe duplicarse)
    simulate --status wamid.Y read       aviso de entrega de un mensaje enviado
Las respuestas del bot se ven en el inbox (http://localhost:5173) y en los logs del worker.
"""

import argparse
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from typing import Any
from uuid import uuid4

import httpx

logger = logging.getLogger("simulador")

DEFAULT_URL = "http://localhost:8000/api/v1/webhook/whatsapp"


def text_payload(phone_number_id: str, sender: str, name: str, message_id: str, body: str) -> Any:
    return _payload(
        phone_number_id,
        {
            "contacts": [{"wa_id": sender, "profile": {"name": name}}],
            "messages": [
                {
                    "id": message_id,
                    "from": sender,
                    "timestamp": str(int(time.time())),
                    "type": "text",
                    "text": {"body": body},
                }
            ],
        },
    )


def status_payload(phone_number_id: str, message_id: str, status: str) -> Any:
    return _payload(phone_number_id, {"statuses": [{"id": message_id, "status": status}]})


def _payload(phone_number_id: str, content: dict[str, Any]) -> Any:
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"phone_number_id": phone_number_id},
        **content,
    }
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": value}]}],
    }


def post_signed(url: str, secret: str, payload: Any) -> int:
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    response = httpx.post(
        url,
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature},
        timeout=10,
    )
    return response.status_code


def main() -> int:
    args = _parse_args()
    if args.status:
        message_id, status = args.status
        payload = status_payload(args.phone_number_id, message_id, status)
    elif args.text:
        message_id = args.id or f"wamid.sim.{uuid4().hex[:12]}"
        payload = text_payload(args.phone_number_id, args.sender, args.name, message_id, args.text)
    else:
        logger.error("Indica un texto o --status ID ESTADO")
        return 2
    for attempt in range(1, args.repeat + 1):
        code = post_signed(args.url, args.secret, payload)
        logger.info("envio %d: %s -> HTTP %d", attempt, message_id, code)
        if code != 200:
            return 1
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("text", nargs="?", help="texto que escribe el cliente")
    parser.add_argument(
        "--from", dest="sender", default="5215550001111", help="telefono del cliente"
    )
    parser.add_argument("--name", default="Cliente Demo", help="nombre de perfil del cliente")
    parser.add_argument("--id", help="id del mensaje (por defecto, uno nuevo)")
    parser.add_argument("--repeat", type=int, default=1, help="enviar el mismo webhook N veces")
    parser.add_argument("--status", nargs=2, metavar=("ID", "ESTADO"), help="aviso de entrega")
    parser.add_argument(
        "--phone-number-id",
        default=os.environ.get("SEED_PHONE_NUMBER_ID", "demo-phone-number-id"),
        help="numero de WhatsApp del negocio (el del seed)",
    )
    parser.add_argument("--url", default=os.environ.get("SIMULATOR_URL", DEFAULT_URL))
    parser.add_argument("--secret", default=os.environ.get("WHATSAPP_APP_SECRET", ""))
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
