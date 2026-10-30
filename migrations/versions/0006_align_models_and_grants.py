"""Alinear los modelos ORM con la base y dar permisos al rol de la app.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-30

Esquema (generado con autogenerate y revisado):
- Columnas que el ORM usaba y no existian: contact.name, conversation.status/assigned_to,
  message.type, webhook_event.updated_at.
- created_at/updated_at pasan a NOT NULL (ya tenian DEFAULT now()).
- Indices por tenant_id en todas las tablas por inquilino, y las FK que declara el ORM.
- Unicos: contact(tenant_id, phone) y webhook_event(tenant_id, provider_message_id).
  El unico anterior de webhook_event usaba channel_account_id, que siempre es NULL, y no
  evitaba duplicados.

Permisos del rol de la app (APP_DB_USER, por defecto bot_app; lo crea infra/db/10-app-role.sh):
- Lectura/escritura en las tablas, tambien en las que creen migraciones futuras.
- Solo lectura en pack y pack_version (catalogo global, sin RLS).
- Sin acceso a alembic_version.
Una migracion futura que cree otra tabla global debe revocar la escritura, como aqui.
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = os.environ.get("APP_DB_USER", "bot_app")
GLOBAL_READ_ONLY_TABLES = ("pack", "pack_version")


def upgrade() -> None:
    _align_schema()
    _grant_app_role()


def _align_schema() -> None:
    op.alter_column(
        "appointment",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "appointment",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_appointment_tenant_id"), "appointment", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_appointment_contact_id_contact"), "appointment", "contact", ["contact_id"], ["id"]
    )
    op.create_foreign_key(
        op.f("fk_appointment_resource_id_resource"),
        "appointment",
        "resource",
        ["resource_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_appointment_service_id_service"), "appointment", "service", ["service_id"], ["id"]
    )
    op.alter_column(
        "audit_log",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_audit_log_tenant_id"), "audit_log", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_audit_log_user_id_user"), "audit_log", "user", ["user_id"], ["id"]
    )
    op.alter_column(
        "campaign",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "campaign",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_campaign_tenant_id"), "campaign", ["tenant_id"], unique=False)
    op.create_index(
        op.f("ix_campaign_recipient_tenant_id"), "campaign_recipient", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_campaign_recipient_campaign_id_campaign"),
        "campaign_recipient",
        "campaign",
        ["campaign_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_campaign_recipient_contact_id_contact"),
        "campaign_recipient",
        "contact",
        ["contact_id"],
        ["id"],
    )
    op.alter_column(
        "catalog",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "catalog",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_catalog_tenant_id"), "catalog", ["tenant_id"], unique=False)
    op.alter_column(
        "catalog_item",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "catalog_item",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_catalog_item_tenant_id"), "catalog_item", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_catalog_item_catalog_id_catalog"),
        "catalog_item",
        "catalog",
        ["catalog_id"],
        ["id"],
    )
    op.alter_column(
        "consent_event",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "consent_event",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(
        op.f("ix_consent_event_tenant_id"), "consent_event", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_consent_event_contact_id_contact"),
        "consent_event",
        "contact",
        ["contact_id"],
        ["id"],
    )
    op.add_column("contact", sa.Column("name", sa.String(), nullable=True))
    op.alter_column(
        "contact",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "contact",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_contact_tenant_id"), "contact", ["tenant_id"], unique=False)
    op.create_unique_constraint("uq_contact_tenant_phone", "contact", ["tenant_id", "phone"])
    op.add_column("conversation", sa.Column("assigned_to", sa.String(), nullable=True))
    op.add_column(
        "conversation", sa.Column("status", sa.String(), server_default="bot", nullable=False)
    )
    op.alter_column(
        "conversation",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "conversation",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_conversation_tenant_id"), "conversation", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_conversation_contact_id_contact"),
        "conversation",
        "contact",
        ["contact_id"],
        ["id"],
    )
    op.alter_column(
        "dead_letter",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_dead_letter_tenant_id"), "dead_letter", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_dead_letter_outbox_message_id_outbox_message"),
        "dead_letter",
        "outbox_message",
        ["outbox_message_id"],
        ["id"],
    )
    op.alter_column(
        "flow_instance",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "flow_instance",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(
        op.f("ix_flow_instance_tenant_id"), "flow_instance", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_flow_instance_conversation_id_conversation"),
        "flow_instance",
        "conversation",
        ["conversation_id"],
        ["id"],
    )
    op.create_index(op.f("ix_item_fitment_tenant_id"), "item_fitment", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_item_fitment_item_id_catalog_item"),
        "item_fitment",
        "catalog_item",
        ["item_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_item_identifier_tenant_id"), "item_identifier", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_item_identifier_item_id_catalog_item"),
        "item_identifier",
        "catalog_item",
        ["item_id"],
        ["id"],
    )
    op.create_index(op.f("ix_item_media_tenant_id"), "item_media", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_item_media_item_id_catalog_item"),
        "item_media",
        "catalog_item",
        ["item_id"],
        ["id"],
    )
    op.alter_column(
        "lead",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "lead",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_lead_tenant_id"), "lead", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_lead_contact_id_contact"), "lead", "contact", ["contact_id"], ["id"]
    )
    op.add_column("message", sa.Column("type", sa.String(), server_default="text", nullable=False))
    op.alter_column(
        "message",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_message_tenant_id"), "message", ["tenant_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_message_conversation_id_conversation"),
        "message",
        "conversation",
        ["conversation_id"],
        ["id"],
    )
    op.alter_column(
        "outbox_message",
        "scheduled_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "outbox_message",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(
        op.f("ix_outbox_message_tenant_id"), "outbox_message", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_outbox_message_conversation_id_conversation"),
        "outbox_message",
        "conversation",
        ["conversation_id"],
        ["id"],
    )
    op.alter_column(
        "pack_version",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_foreign_key(
        op.f("fk_pack_version_pack_id_pack"), "pack_version", "pack", ["pack_id"], ["id"]
    )
    op.alter_column(
        "resource",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "resource",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_resource_tenant_id"), "resource", ["tenant_id"], unique=False)
    op.alter_column(
        "service",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "service",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_service_tenant_id"), "service", ["tenant_id"], unique=False)
    op.create_index(
        op.f("ix_suppression_list_tenant_id"), "suppression_list", ["tenant_id"], unique=False
    )
    op.alter_column(
        "tenant",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "tenant",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "tenant_membership",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(
        op.f("ix_tenant_membership_tenant_id"), "tenant_membership", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_tenant_membership_user_id_user"), "tenant_membership", "user", ["user_id"], ["id"]
    )
    op.create_index(
        op.f("ix_tenant_pack_binding_tenant_id"), "tenant_pack_binding", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_tenant_pack_binding_pack_id_pack"),
        "tenant_pack_binding",
        "pack",
        ["pack_id"],
        ["id"],
    )
    op.alter_column(
        "user",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "user",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index(op.f("ix_user_tenant_id"), "user", ["tenant_id"], unique=False)
    op.add_column(
        "webhook_event",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.alter_column(
        "webhook_event",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(op.f("uq_webhook_provider_msg"), "webhook_event", type_="unique")
    op.create_index(
        op.f("ix_webhook_event_tenant_id"), "webhook_event", ["tenant_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_webhook_event_tenant_provider_msg",
        "webhook_event",
        ["tenant_id", "provider_message_id"],
    )


def _grant_app_role() -> None:
    role = f'"{APP_ROLE}"'
    op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {role}"
    )
    for table in GLOBAL_READ_ONLY_TABLES:
        op.execute(f"REVOKE INSERT, UPDATE, DELETE ON {table} FROM {role}")
    op.execute(f"REVOKE ALL ON alembic_version FROM {role}")


def _revoke_app_role() -> None:
    role = f'"{APP_ROLE}"'
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {role}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM {role}"
    )
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role}")


def downgrade() -> None:
    _revoke_app_role()
    _unalign_schema()


def _unalign_schema() -> None:
    op.drop_constraint("uq_webhook_event_tenant_provider_msg", "webhook_event", type_="unique")
    op.drop_index(op.f("ix_webhook_event_tenant_id"), table_name="webhook_event")
    op.create_unique_constraint(
        op.f("uq_webhook_provider_msg"),
        "webhook_event",
        ["channel_account_id", "provider_message_id"],
        postgresql_nulls_not_distinct=False,
    )
    op.alter_column(
        "webhook_event",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_column("webhook_event", "updated_at")
    op.drop_index(op.f("ix_user_tenant_id"), table_name="user")
    op.alter_column(
        "user",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "user",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(
        op.f("fk_tenant_pack_binding_pack_id_pack"), "tenant_pack_binding", type_="foreignkey"
    )
    op.drop_index(op.f("ix_tenant_pack_binding_tenant_id"), table_name="tenant_pack_binding")
    op.drop_constraint(
        op.f("fk_tenant_membership_user_id_user"), "tenant_membership", type_="foreignkey"
    )
    op.drop_index(op.f("ix_tenant_membership_tenant_id"), table_name="tenant_membership")
    op.alter_column(
        "tenant_membership",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "tenant",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "tenant",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_index(op.f("ix_suppression_list_tenant_id"), table_name="suppression_list")
    op.drop_index(op.f("ix_service_tenant_id"), table_name="service")
    op.alter_column(
        "service",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "service",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_index(op.f("ix_resource_tenant_id"), table_name="resource")
    op.alter_column(
        "resource",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "resource",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(op.f("fk_pack_version_pack_id_pack"), "pack_version", type_="foreignkey")
    op.alter_column(
        "pack_version",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(
        op.f("fk_outbox_message_conversation_id_conversation"), "outbox_message", type_="foreignkey"
    )
    op.drop_index(op.f("ix_outbox_message_tenant_id"), table_name="outbox_message")
    op.alter_column(
        "outbox_message",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "outbox_message",
        "scheduled_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(
        op.f("fk_message_conversation_id_conversation"), "message", type_="foreignkey"
    )
    op.drop_index(op.f("ix_message_tenant_id"), table_name="message")
    op.alter_column(
        "message",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_column("message", "type")
    op.drop_constraint(op.f("fk_lead_contact_id_contact"), "lead", type_="foreignkey")
    op.drop_index(op.f("ix_lead_tenant_id"), table_name="lead")
    op.alter_column(
        "lead",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "lead",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(op.f("fk_item_media_item_id_catalog_item"), "item_media", type_="foreignkey")
    op.drop_index(op.f("ix_item_media_tenant_id"), table_name="item_media")
    op.drop_constraint(
        op.f("fk_item_identifier_item_id_catalog_item"), "item_identifier", type_="foreignkey"
    )
    op.drop_index(op.f("ix_item_identifier_tenant_id"), table_name="item_identifier")
    op.drop_constraint(
        op.f("fk_item_fitment_item_id_catalog_item"), "item_fitment", type_="foreignkey"
    )
    op.drop_index(op.f("ix_item_fitment_tenant_id"), table_name="item_fitment")
    op.drop_constraint(
        op.f("fk_flow_instance_conversation_id_conversation"), "flow_instance", type_="foreignkey"
    )
    op.drop_index(op.f("ix_flow_instance_tenant_id"), table_name="flow_instance")
    op.alter_column(
        "flow_instance",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "flow_instance",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(
        op.f("fk_dead_letter_outbox_message_id_outbox_message"), "dead_letter", type_="foreignkey"
    )
    op.drop_index(op.f("ix_dead_letter_tenant_id"), table_name="dead_letter")
    op.alter_column(
        "dead_letter",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(
        op.f("fk_conversation_contact_id_contact"), "conversation", type_="foreignkey"
    )
    op.drop_index(op.f("ix_conversation_tenant_id"), table_name="conversation")
    op.alter_column(
        "conversation",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "conversation",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_column("conversation", "status")
    op.drop_column("conversation", "assigned_to")
    op.drop_constraint("uq_contact_tenant_phone", "contact", type_="unique")
    op.drop_index(op.f("ix_contact_tenant_id"), table_name="contact")
    op.alter_column(
        "contact",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "contact",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_column("contact", "name")
    op.drop_constraint(
        op.f("fk_consent_event_contact_id_contact"), "consent_event", type_="foreignkey"
    )
    op.drop_index(op.f("ix_consent_event_tenant_id"), table_name="consent_event")
    op.alter_column(
        "consent_event",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "consent_event",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(
        op.f("fk_catalog_item_catalog_id_catalog"), "catalog_item", type_="foreignkey"
    )
    op.drop_index(op.f("ix_catalog_item_tenant_id"), table_name="catalog_item")
    op.alter_column(
        "catalog_item",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "catalog_item",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_index(op.f("ix_catalog_tenant_id"), table_name="catalog")
    op.alter_column(
        "catalog",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "catalog",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(
        op.f("fk_campaign_recipient_contact_id_contact"), "campaign_recipient", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_campaign_recipient_campaign_id_campaign"), "campaign_recipient", type_="foreignkey"
    )
    op.drop_index(op.f("ix_campaign_recipient_tenant_id"), table_name="campaign_recipient")
    op.drop_index(op.f("ix_campaign_tenant_id"), table_name="campaign")
    op.alter_column(
        "campaign",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "campaign",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(op.f("fk_audit_log_user_id_user"), "audit_log", type_="foreignkey")
    op.drop_index(op.f("ix_audit_log_tenant_id"), table_name="audit_log")
    op.alter_column(
        "audit_log",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint(op.f("fk_appointment_service_id_service"), "appointment", type_="foreignkey")
    op.drop_constraint(
        op.f("fk_appointment_resource_id_resource"), "appointment", type_="foreignkey"
    )
    op.drop_constraint(op.f("fk_appointment_contact_id_contact"), "appointment", type_="foreignkey")
    op.drop_index(op.f("ix_appointment_tenant_id"), table_name="appointment")
    op.alter_column(
        "appointment",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "appointment",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
