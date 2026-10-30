"""Datos de demostracion: inquilino, numero de WhatsApp y usuario admin. Es idempotente.

Uso (dentro del contenedor de la API, lo hace botConfigurable.bat en cada arranque):
    python scripts/seed.py --demo

Corre como dueno de las tablas (DATABASE_OWNER_URL): crea datos de varios inquilinos.
La contrasena del admin solo se fija al crearlo; si ya existe no se cambia.
"""

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User
from auth.password import PasswordService
from core.db import create_engine, create_session_factory
from core.models import Tenant
from messaging.models import ChannelAccount

logger = logging.getLogger("seed")


@dataclass(frozen=True)
class DemoData:
    tenant_id: str = "demo"
    tenant_name: str = "Negocio Demo"
    phone_number_id: str = os.environ.get("SEED_PHONE_NUMBER_ID", "demo-phone-number-id")
    display_number: str = "+52 55 0000 0000"
    admin_email: str = os.environ.get("SEED_ADMIN_EMAIL", "admin@demo.local")
    admin_password: str = os.environ.get("SEED_ADMIN_PASSWORD", "demo-admin-2026")


async def seed_demo(session: AsyncSession, data: DemoData) -> None:
    await session.execute(
        insert(Tenant)
        .values(id=data.tenant_id, name=data.tenant_name)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(
        insert(ChannelAccount)
        .values(
            tenant_id=data.tenant_id,
            provider="whatsapp",
            phone_number_id=data.phone_number_id,
            display_number=data.display_number,
        )
        .on_conflict_do_nothing(constraint="uq_channel_account_provider_phone")
    )
    existing = await session.scalar(select(User.id).where(User.email == data.admin_email))
    if existing is None:
        session.add(
            User(
                tenant_id=data.tenant_id,
                email=data.admin_email,
                password_hash=PasswordService().hash(data.admin_password),
                role="admin",
            )
        )
        logger.info("Usuario admin creado: %s", data.admin_email)
    logger.info(
        "Seed demo listo: inquilino=%s phone_number_id=%s admin=%s",
        data.tenant_id,
        data.phone_number_id,
        data.admin_email,
    )


async def main(demo: bool) -> None:
    if not demo:
        logger.info("Nada que hacer. Usa --demo para crear los datos de demostracion.")
        return
    url = os.environ.get("DATABASE_OWNER_URL") or os.environ["DATABASE_URL"]
    engine = create_engine(url)
    try:
        async with create_session_factory(engine)() as session, session.begin():
            await seed_demo(session, DemoData())
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="crear los datos de demostracion")
    asyncio.run(main(parser.parse_args().demo))
