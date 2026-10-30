import hashlib
import hmac

from core.security import constant_time_equals, verify_signature

SECRET = "app-secret"
BODY = b'{"entry": []}'


def _signature(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_accepts_valid_signature() -> None:
    assert verify_signature(SECRET, BODY, _signature(BODY))


def test_rejects_signature_from_other_secret() -> None:
    assert not verify_signature(SECRET, BODY, _signature(BODY, secret="otro"))


def test_rejects_tampered_body() -> None:
    assert not verify_signature(SECRET, BODY + b" ", _signature(BODY))


def test_rejects_missing_or_malformed_header() -> None:
    assert not verify_signature(SECRET, BODY, "")
    assert not verify_signature(SECRET, BODY, _signature(BODY).removeprefix("sha256="))


def test_constant_time_equals() -> None:
    assert constant_time_equals("token", "token")
    assert not constant_time_equals("token", "otro")
