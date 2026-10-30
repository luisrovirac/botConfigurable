from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt

TokenType = Literal["access", "refresh"]


class InvalidTokenError(Exception):
    """El token no es valido, expiro o no es del tipo esperado."""


class TokenService:
    """Emite y valida JWT. Cada token lleva `type`, asi un refresh no sirve como access."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._ttl: dict[TokenType, timedelta] = {"access": access_ttl, "refresh": refresh_ttl}

    def create(
        self, token_type: TokenType, subject: str, claims: dict[str, Any] | None = None
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            **(claims or {}),
            "sub": subject,
            "type": token_type,
            "iat": now,
            "exp": now + self._ttl[token_type],
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode(self, token: str, expected_type: TokenType) -> dict[str, Any]:
        try:
            payload: dict[str, Any] = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        if payload.get("type") != expected_type:
            raise InvalidTokenError(f"Se esperaba un token '{expected_type}'")
        return payload
