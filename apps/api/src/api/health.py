from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

router = APIRouter(tags=["salud"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """El proceso esta vivo (no revisa dependencias)."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request, response: Response) -> dict[str, str]:
    """Listo para recibir trafico: la base de datos responde."""
    database = await _check_database(request.app.state.session_factory)
    ready = database == "ok"
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "not_ready", "database": database}


async def _check_database(session_factory: async_sessionmaker[AsyncSession]) -> str:
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        return f"error: {type(exc).__name__}"
    return "ok"
