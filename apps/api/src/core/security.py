import hashlib
import hmac

_SIGNATURE_PREFIX = "sha256="


def verify_signature(app_secret: str, payload: bytes, signature_header: str) -> bool:
    """Valida la cabecera X-Hub-Signature-256 de Meta sobre el cuerpo crudo."""
    if not signature_header.startswith(_SIGNATURE_PREFIX):
        return False
    expected = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix(_SIGNATURE_PREFIX)
    return hmac.compare_digest(expected, received)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
