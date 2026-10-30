from argon2 import PasswordHasher

from auth.password import PasswordService

# Parametros bajos para que los tests sean rapidos; el comportamiento es el mismo.
FAST = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)


def test_verify_accepts_correct_password() -> None:
    service = PasswordService(FAST)
    assert service.verify("clave-segura", service.hash("clave-segura"))


def test_verify_rejects_wrong_password() -> None:
    service = PasswordService(FAST)
    assert not service.verify("otra", service.hash("clave-segura"))


def test_verify_rejects_malformed_hash() -> None:
    assert not PasswordService(FAST).verify("clave", "no-es-un-hash")


def test_hash_is_salted() -> None:
    service = PasswordService(FAST)
    assert service.hash("clave") != service.hash("clave")


def test_needs_rehash_when_parameters_change() -> None:
    old_hash = PasswordService(FAST).hash("clave")
    assert PasswordService().needs_rehash(old_hash)
    assert not PasswordService(FAST).needs_rehash(old_hash)
