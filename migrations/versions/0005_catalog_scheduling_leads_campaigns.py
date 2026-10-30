"""catalog_scheduling_leads_campaigns

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # catalog
    op.create_table(
        'catalog', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('schema_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'catalog_item', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('catalog_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sku', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=True),
        sa.Column('attributes', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'item_identifier', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('value_normalized', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'item_fitment', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('brand', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('year_from', sa.Integer(), nullable=False),
        sa.Column('year_to', sa.Integer(), nullable=False),
        sa.Column('engine', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'item_media', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    # scheduling
    op.create_table(
        'service', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'resource', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'appointment', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('external_event_id', sa.String(), nullable=True),
        sa.Column('sync_token', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    # leads
    op.create_table(
        'lead', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('utm', postgresql.JSONB(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('stage', sa.String(), nullable=False, server_default='new'),
        sa.Column('assigned_to', sa.String(), nullable=True),
        sa.Column('ghl_contact_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    # campaigns
    op.create_table(
        'campaign', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('template_name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('segment', postgresql.JSONB(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'campaign_recipient', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    # consent
    op.create_table(
        'consent_event', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('text_exact', sa.Text(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'suppression_list', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # packs
    op.create_table(
        'pack', sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'pack_version', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pack_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('checksum', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'tenant_pack_binding', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('pack_id', sa.String(), nullable=False),
        sa.Column('pack_version', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )
    # RLS
    for table in ['catalog', 'catalog_item', 'item_identifier', 'item_fitment', 'item_media', 
                  'service', 'resource', 'appointment', 'lead', 'campaign', 'campaign_recipient',
                  'consent_event', 'suppression_list', 'tenant_pack_binding']:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        op.execute(f'''
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
        ''')
    op.create_index('ix_item_identifier_normalized', 'item_identifier', ['value_normalized'])


def downgrade() -> None:
    op.drop_index('ix_item_identifier_normalized')
    for table in ['catalog', 'catalog_item', 'item_identifier', 'item_fitment', 'item_media', 
                  'service', 'resource', 'appointment', 'lead', 'campaign', 'campaign_recipient',
                  'consent_event', 'suppression_list', 'tenant_pack_binding']:
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')
    op.drop_table('tenant_pack_binding')
    op.drop_table('pack_version')
    op.drop_table('pack')
    op.drop_table('suppression_list')
    op.drop_table('consent_event')
    op.drop_table('campaign_recipient')
    op.drop_table('campaign')
    op.drop_table('lead')
    op.drop_table('appointment')
    op.drop_table('resource')
    op.drop_table('service')
    op.drop_table('item_media')
    op.drop_table('item_fitment')
    op.drop_table('item_identifier')
    op.drop_table('catalog_item')
    op.drop_table('catalog')
