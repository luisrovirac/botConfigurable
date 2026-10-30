"""rls

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    tables = ['tenant', 'webhook_event', 'contact', 'conversation', 'message', 'outbox_message', 'dead_letter']
    for table in tables:
        # En la tabla tenant el identificador del inquilino es su clave primaria (id);
        # en las demas es la columna tenant_id.
        column = 'id' if table == 'tenant' else 'tenant_id'
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        op.execute(f'''
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING ({column} = current_setting('app.tenant_id', true))
            WITH CHECK ({column} = current_setting('app.tenant_id', true));
        ''')


def downgrade() -> None:
    tables = ['tenant', 'webhook_event', 'contact', 'conversation', 'message', 'outbox_message', 'dead_letter']
    for table in tables:
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')
