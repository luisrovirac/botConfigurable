"""Dependencias de FastAPI: aqui se ensamblan los servicios que usan las rutas."""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from messaging.inbound_pipeline import InboundPipeline


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


def get_inbound_pipeline() -> InboundPipeline:
    return InboundPipeline()
