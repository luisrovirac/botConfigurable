"""Reglas de la base de datos que deben cumplirse siempre."""

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import AsyncEngine

from db_models import Base

# Tablas globales (no pertenecen a un inquilino) que por eso no llevan RLS.
GLOBAL_TABLES = {"pack", "pack_version", "alembic_version"}


async def test_every_tenant_table_has_rls_enabled_and_a_policy(owner_engine: AsyncEngine) -> None:
    async with owner_engine.connect() as conn:
        rows = await conn.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, count(p.polname) AS policies
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
                LEFT JOIN pg_policy p ON p.polrelid = c.oid
                WHERE c.relkind = 'r'
                GROUP BY c.relname, c.relrowsecurity
                """
            )
        )
        tables = {name: (rls, policies) for name, rls, policies in rows}

    unprotected = {
        name
        for name, (rls, policies) in tables.items()
        if name not in GLOBAL_TABLES and (not rls or policies == 0)
    }
    assert unprotected == set(), f"Tablas sin RLS o sin politica: {sorted(unprotected)}"


def _schema_diff(connection: Connection) -> list[object]:
    context = MigrationContext.configure(connection, opts={"compare_type": True})
    return list(compare_metadata(context, Base.metadata))


async def test_orm_models_match_the_migrated_schema(owner_engine: AsyncEngine) -> None:
    """Si falla: falta una migracion o un modelo quedo distinto a la base."""
    async with owner_engine.connect() as conn:
        diff = await conn.run_sync(_schema_diff)
    assert diff == []
