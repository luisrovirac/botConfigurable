"""Consultas que cruzan inquilinos, a traves de funciones SQL SECURITY DEFINER (ADR 0005).

Son las unicas excepciones a RLS: el rol de la app no puede leer esas tablas sin inquilino,
solo ejecutar estas funciones, que devuelven lo minimo necesario.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class LoginCandidate:
    user_id: UUID
    tenant_id: str
    password_hash: str
    role: str
    is_active: bool


class TenantDirectory:
    async def resolve_by_phone_number_id(
        self, session: AsyncSession, phone_number_id: str
    ) -> str | None:
        """Inquilino duenio del numero de WhatsApp, o None si no esta registrado."""
        tenant_id: str | None = await session.scalar(
            text("SELECT resolve_tenant_by_phone_number_id(:id)"), {"id": phone_number_id}
        )
        return tenant_id

    async def find_user_for_login(self, session: AsyncSession, email: str) -> LoginCandidate | None:
        row = (
            await session.execute(
                text(
                    "SELECT id, tenant_id, password_hash, role, is_active "
                    "FROM find_user_for_login(:email)"
                ),
                {"email": email},
            )
        ).first()
        if row is None:
            return None
        return LoginCandidate(
            user_id=row.id,
            tenant_id=row.tenant_id,
            password_hash=row.password_hash,
            role=row.role,
            is_active=row.is_active,
        )

    async def tenants_with_pending_work(self, session: AsyncSession) -> list[str]:
        result = await session.execute(text("SELECT tenants_with_pending_work()"))
        return list(result.scalars())
