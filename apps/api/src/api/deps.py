"""Dependencias de FastAPI. Los servicios se crean en el lifespan (api.main) y se leen aqui."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from auth.service import AuthenticationError, AuthService, Principal
from core.config import Settings
from core.tenant import set_tenant
from inbox.queries import InboxQueries
from messaging.webhook_ingest import WebhookIngestor

_bearer = HTTPBearer(auto_error=False)


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Una transaccion por peticion (unidad de trabajo).

    Hace commit si la ruta termina bien y rollback si lanza una excepcion.
    Los servicios nunca hacen commit por su cuenta.
    """
    async with request.app.state.session_factory() as session, session.begin():
        yield session


def get_webhook_ingestor(request: Request) -> WebhookIngestor:
    ingestor: WebhookIngestor = request.app.state.webhook_ingestor
    return ingestor


def get_auth_service(request: Request) -> AuthService:
    service: AuthService = request.app.state.auth_service
    return service


def get_inbox_queries() -> InboxQueries:
    return InboxQueries()


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> Principal:
    if credentials is None:
        raise _unauthorized("Falta el token de acceso")
    try:
        return auth.authenticate(credentials.credentials)
    except AuthenticationError as exc:
        raise _unauthorized(str(exc)) from exc


async def get_tenant_session(
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncSession:
    """Sesion con el inquilino del usuario autenticado fijado (RLS filtra el resto)."""
    await set_tenant(session, principal.tenant_id)
    return session


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
