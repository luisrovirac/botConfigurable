import hmac
import hashlib


def verify_signature(app_secret: str, payload: bytes, signature_header: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()
    received = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, received)
