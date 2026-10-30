"""Worker de mensajeria: procesa la cola de entrada y envia el outbox en bucle.

Composition root del worker. La logica de cada vuelta esta en messaging/worker_cycle.py.
Se detiene limpio con SIGTERM/SIGINT (docker stop, Ctrl+C).
"""

import asyncio
import contextlib
import signal
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx
import structlog

from core.config import Settings, get_settings
from core.db import create_engine, create_session_factory
from core.logging import configure_logging
from messaging.factory import build_channel_adapter, build_worker_cycle

# El healthcheck de docker compose revisa que este archivo se actualice seguido.
HEARTBEAT_FILE = Path("/tmp/worker.heartbeat")  # noqa: S108 - archivo local del contenedor
FAILURE_BACKOFF_SECONDS = 5.0

logger = structlog.get_logger(__name__)


async def run(settings: Settings) -> None:
    engine = create_engine(settings.database_url)
    stop = _stop_event()
    poll_interval = settings.worker_poll_interval_ms / 1000
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            adapter = build_channel_adapter(settings, http)
            cycle = build_worker_cycle(settings, create_session_factory(engine), adapter)
            logger.info("worker_started", send_mode=settings.whatsapp_send_mode)
            while not stop.is_set():
                processed = await _run_cycle_safely(cycle.run_once)
                HEARTBEAT_FILE.write_text(str(time.time()))
                if processed is None:  # fallo: esperar mas para no inundar los logs
                    await _wait(stop, FAILURE_BACKOFF_SECONDS)
                elif processed == 0:
                    await _wait(stop, poll_interval)
    finally:
        await engine.dispose()
        logger.info("worker_stopped")


async def _run_cycle_safely(run_once: Callable[[], Awaitable[int]]) -> int | None:
    """Cantidad procesada, o None si la vuelta fallo."""
    try:
        return await run_once()
    except Exception:  # limite del proceso: se registra y el bucle sigue
        logger.exception("worker_cycle_failed")
        return None


def _stop_event() -> asyncio.Event:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        # En Windows no hay add_signal_handler: alli solo funciona Ctrl+C (KeyboardInterrupt).
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    return stop


async def _wait(stop: asyncio.Event, seconds: float) -> None:
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
