from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


class PasswordService:
    """Hash y verificacion de contrasenas con argon2id."""

    def __init__(self, hasher: PasswordHasher | None = None) -> None:
        self._hasher = hasher or PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """True si el hash usa parametros viejos y conviene regenerarlo tras un login correcto."""
        return self._hasher.check_needs_rehash(password_hash)
