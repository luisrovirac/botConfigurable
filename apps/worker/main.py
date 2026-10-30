import asyncio

import structlog


async def main() -> None:
    logger = structlog.get_logger()
    logger.info("worker_starting")


if __name__ == "__main__":
    asyncio.run(main())
