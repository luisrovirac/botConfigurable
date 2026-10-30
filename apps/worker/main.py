"""Worker de mensajeria.

Pendiente (Etapa 2, docs/05-plan-mejoras.md 2.6): bucle que procesa eventos entrantes y el
outbox. Mientras tanto, el servicio `worker` de docker compose esta en un perfil opcional.
"""

import structlog

from core.config import get_settings
from core.logging import configure_logging


def main() -> None:
    configure_logging(get_settings().log_level)
    structlog.get_logger(__name__).warning(
        "worker_not_implemented", detail="El bucle del worker llega en la Etapa 2"
    )


if __name__ == "__main__":
    main()
