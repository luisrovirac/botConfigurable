from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt import InvalidTokenError, TokenService, TokenType
from auth.models import User
from auth.password import PasswordService
from core.tenant import set_tenant
from core.tenant_directory import TenantDirectory


class AuthenticationError(Exception):
    """Credenciales o token invalidos. El mensaje no revela cual de los datos fallo."""


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class Principal:
    """Usuario autenticado. Su tenant_id viene del token firmado, nunca del cliente."""

    user_id: UUID
    tenant_id: str
    role: str


class AuthService:
    def __init__(
        self, directory: TenantDirectory, passwords: PasswordService, tokens: TokenService
    ) -> None:
        self._directory = directory
        self._passwords = passwords
        self._tokens = tokens
        # Para emails inexistentes se verifica contra este hash: la respuesta tarda lo mismo
        # y no revela que emails estan registrados.
        self._dummy_hash = passwords.hash("dummy-password-para-tiempo-constante")

    async def login(self, session: AsyncSession, email: str, password: str) -> TokenPair:
        candidate = await self._directory.find_user_for_login(session, email)
        password_hash = candidate.password_hash if candidate else self._dummy_hash
        valid = self._passwords.verify(password, password_hash)
        if candidate is None or not candidate.is_active or not valid:
            raise AuthenticationError("Email o contrasena incorrectos")
        return self._issue(Principal(candidate.user_id, candidate.tenant_id, candidate.role))

    async def refresh(self, session: AsyncSession, refresh_token: str) -> TokenPair:
        """Emite un par nuevo si el usuario sigue activo."""
        principal = self._principal(refresh_token, "refresh")
        await set_tenant(session, principal.tenant_id)
        user = await session.scalar(select(User).where(User.id == principal.user_id))
        if user is None or not user.is_active:
            raise AuthenticationError("Usuario inactivo o inexistente")
        return self._issue(Principal(user.id, user.tenant_id, user.role))

    def authenticate(self, access_token: str) -> Principal:
        return self._principal(access_token, "access")

    def _issue(self, principal: Principal) -> TokenPair:
        claims = {"tenant_id": principal.tenant_id, "role": principal.role}
        subject = str(principal.user_id)
        return TokenPair(
            access_token=self._tokens.create("access", subject, claims),
            refresh_token=self._tokens.create("refresh", subject, claims),
        )

    def _principal(self, token: str, token_type: TokenType) -> Principal:
        try:
            claims = self._tokens.decode(token, token_type)
            return Principal(UUID(claims["sub"]), str(claims["tenant_id"]), str(claims["role"]))
        except (InvalidTokenError, KeyError, ValueError) as exc:
            raise AuthenticationError("Token invalido") from exc
