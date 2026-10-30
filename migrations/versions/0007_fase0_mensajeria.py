"""Fase 0: cuentas de canal, cola de entrada, estados de entrega y funciones sin contexto.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-30

- channel_account: numero de WhatsApp de cada inquilino (resuelve el inquilino del webhook).
- webhook_event pasa a ser la cola de entrada del worker (status, process_after, attempts).
  Los eventos ya procesados (processed = true) quedan como status 'done'.
- message: estado y id del proveedor para los salientes; created_at con clock_timestamp().
  outbox_message apunta a su message.
- message_status_event: avisos de entrega del proveedor.
- Unicos: un flow_instance por conversacion y un registro de supresion por telefono.

Funciones SECURITY DEFINER (ADR 0005). Son las unicas consultas que cruzan inquilinos; el rol
de la app solo puede ejecutarlas, no leer las tablas sin inquilino:
- resolve_tenant_by_phone_number_id(text): inquilino de un webhook.
- find_user_for_login(text): usuario por email, antes de conocer su inquilino.
- tenants_with_pending_work(): inquilinos con trabajo para el worker.
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = os.environ.get("APP_DB_USER", "bot_app")
NEW_TENANT_TABLES = ("channel_account", "message_status_event")

FUNCTIONS = {
    "resolve_tenant_by_phone_number_id(text)": """
        CREATE FUNCTION resolve_tenant_by_phone_number_id(p_phone_number_id text)
        RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT tenant_id FROM channel_account
            WHERE provider = 'whatsapp' AND phone_number_id = p_phone_number_id AND is_active
        $$""",
    "find_user_for_login(text)": """
        CREATE FUNCTION find_user_for_login(p_email text)
        RETURNS TABLE (id uuid, tenant_id text, password_hash text, role text, is_active boolean)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT u.id, u.tenant_id, u.password_hash, u.role, u.is_active
            FROM "user" u WHERE lower(u.email) = lower(p_email)
        $$""",
    "tenants_with_pending_work()": """
        CREATE FUNCTION tenants_with_pending_work()
        RETURNS SETOF text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT tenant_id FROM webhook_event
            WHERE status = 'pending' AND process_after <= now()
            UNION
            SELECT tenant_id FROM outbox_message
            WHERE status = 'pending' AND scheduled_at <= now()
        $$""",
}


def upgrade() -> None:
    _create_tables()
    _alter_existing_tables()
    _migrate_webhook_event_to_queue()
    _enable_rls(NEW_TENANT_TABLES)
    _create_functions()


def downgrade() -> None:
    for signature in FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {signature}")
    _restore_webhook_event()
    op.drop_constraint("uq_suppression_tenant_phone", "suppression_list", type_="unique")
    op.drop_constraint("fk_outbox_message_message_id_message", "outbox_message", type_="foreignkey")
    op.drop_index("ix_outbox_message_pending", table_name="outbox_message")
    op.drop_column("outbox_message", "message_id")
    op.drop_index("ix_message_provider_message_id", table_name="message")
    op.drop_index("ix_message_conversation_created", table_name="message")
    op.drop_column("message", "provider_message_id")
    op.drop_column("message", "status")
    op.alter_column("message", "created_at", server_default=sa.text("now()"))
    op.drop_constraint("uq_flow_instance_conversation", "flow_instance", type_="unique")
    op.drop_constraint(
        "fk_conversation_channel_account_id_channel_account", "conversation", type_="foreignkey"
    )
    op.drop_column("conversation", "channel_account_id")
    op.drop_table("message_status_event")
    op.drop_table("channel_account")


def _create_tables() -> None:
    op.create_table(
        "channel_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("phone_number_id", sa.String(), nullable=False),
        sa.Column("display_number", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "phone_number_id", name="uq_channel_account_provider_phone"
        ),
    )
    op.create_index("ix_channel_account_tenant_id", "channel_account", ["tenant_id"])
    op.create_table(
        "message_status_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("provider_message_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "provider_message_id", "status", name="uq_message_status_event"
        ),
    )
    op.create_index("ix_message_status_event_tenant_id", "message_status_event", ["tenant_id"])


def _alter_existing_tables() -> None:
    op.add_column("conversation", sa.Column("channel_account_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_conversation_channel_account_id_channel_account",
        "conversation",
        "channel_account",
        ["channel_account_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_flow_instance_conversation", "flow_instance", ["conversation_id"]
    )
    # Horas distintas y crecientes para los mensajes de una misma transaccion (orden del inbox).
    op.alter_column("message", "created_at", server_default=sa.text("clock_timestamp()"))
    op.add_column("message", sa.Column("status", sa.String(), nullable=True))
    op.add_column("message", sa.Column("provider_message_id", sa.String(), nullable=True))
    op.create_index("ix_message_conversation_created", "message", ["conversation_id", "created_at"])
    op.create_index("ix_message_provider_message_id", "message", ["provider_message_id"])
    op.add_column("outbox_message", sa.Column("message_id", sa.Uuid(), nullable=True))
    op.create_index("ix_outbox_message_pending", "outbox_message", ["status", "scheduled_at"])
    op.create_foreign_key(
        "fk_outbox_message_message_id_message", "outbox_message", "message", ["message_id"], ["id"]
    )
    op.create_unique_constraint(
        "uq_suppression_tenant_phone", "suppression_list", ["tenant_id", "phone"]
    )


def _migrate_webhook_event_to_queue() -> None:
    op.add_column("webhook_event", sa.Column("sender_phone", sa.String(), nullable=True))
    op.add_column(
        "webhook_event", sa.Column("status", sa.String(), server_default="pending", nullable=False)
    )
    op.add_column(
        "webhook_event",
        sa.Column(
            "process_after",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "webhook_event",
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("webhook_event", sa.Column("last_error", sa.Text(), nullable=True))
    op.execute("UPDATE webhook_event SET status = 'done' WHERE processed")
    op.drop_column("webhook_event", "processed")
    # La columna era texto y siempre NULL; pasa a uuid con FK a channel_account.
    op.alter_column(
        "webhook_event",
        "channel_account_id",
        existing_type=sa.VARCHAR(),
        type_=sa.Uuid(),
        existing_nullable=True,
        postgresql_using="channel_account_id::uuid",
    )
    op.create_foreign_key(
        "fk_webhook_event_channel_account_id_channel_account",
        "webhook_event",
        "channel_account",
        ["channel_account_id"],
        ["id"],
    )
    op.create_index("ix_webhook_event_pending", "webhook_event", ["status", "process_after"])


def _restore_webhook_event() -> None:
    op.drop_index("ix_webhook_event_pending", table_name="webhook_event")
    op.drop_constraint(
        "fk_webhook_event_channel_account_id_channel_account", "webhook_event", type_="foreignkey"
    )
    op.alter_column(
        "webhook_event",
        "channel_account_id",
        existing_type=sa.Uuid(),
        type_=sa.VARCHAR(),
        existing_nullable=True,
        postgresql_using="channel_account_id::text",
    )
    op.add_column(
        "webhook_event",
        sa.Column("processed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute("UPDATE webhook_event SET processed = (status = 'done')")
    for column in ("last_error", "attempts", "process_after", "status", "sender_phone"):
        op.drop_column("webhook_event", column)


def _enable_rls(tables: Sequence[str]) -> None:
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
            """
        )


def _create_functions() -> None:
    for signature, ddl in FUNCTIONS.items():
        op.execute(ddl)
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f'GRANT EXECUTE ON FUNCTION {signature} TO "{APP_ROLE}"')
