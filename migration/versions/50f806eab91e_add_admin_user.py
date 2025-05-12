"""add admin user

Revision ID: 50f806eab91e
Revises: 66bb3081faba
Create Date: 2025-05-12 15:26:22.892469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50f806eab91e'
down_revision: Union[str, None] = '66bb3081faba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    insert into users (id, name, role, api_key, visibility) values (uuid_generate_v4(), 'Admin', 'ADMIN', 'key-' || uuid_generate_v4()::TEXT, 'ACTIVE');
    insert into instruments (name, ticker) values ('Russian Ruble', 'RUB');
    """)
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT * FROM users WHERE role = 'ADMIN';"))
    print("\nРезультат запроса:")
    for row in result:
        print(row)


def downgrade() -> None:
    """Downgrade schema."""
    pass
