from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session

router = APIRouter(tags=["salud"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """El proceso esta vivo (no revisa dependencias)."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(
    request: Request, response: Response, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    """Listo para recibir trafico: la base y Redis responden."""
    checks = {
        "database": await _check_database(session),
        "redis": await _check_redis(request.app.state.redis),
    }
    ready = all(result == "ok" for result in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "not_ready", **checks}


async def _check_database(session: AsyncSession) -> str:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return f"error: {type(exc).__name__}"
    return "ok"


async def _check_redis(redis: Redis) -> str:
    try:
        await redis.ping()
    except (RedisError, OSError) as exc:
        return f"error: {type(exc).__name__}"
    return "ok"
