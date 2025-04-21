"""Rename directionenun to directionenum

Revision ID: b5c28348460d
Revises: cfa51c3c06de
Create Date: 2025-04-21 12:14:54.473046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b5c28348460d'
down_revision: Union[str, None] = 'cfa51c3c06de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Сначала создаем новый тип
    op.execute("CREATE TYPE directionenum AS ENUM ('BUY', 'SELL')")
    # Затем меняем тип колонки
    op.alter_column('orders', 'direction',
                   type_=sa.Enum('BUY', 'SELL', name='directionenum'),
                   postgresql_using='direction::text::directionenum')
    # Удаляем старый тип (если нужно)
    op.execute("DROP TYPE directionenun")

def downgrade() -> None:
    op.execute("CREATE TYPE directionenun AS ENUM ('BUY', 'SELL')")
    op.alter_column('orders', 'direction',
                   type_=postgresql.ENUM('BUY', 'SELL', name='directionenun'),
                   postgresql_using='direction::text::directionenun')
    op.execute("DROP TYPE directionenum")
