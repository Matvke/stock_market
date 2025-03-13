"""Initial revision

Revision ID: 37598a4f00fb
Revises: e27c1a766c49
Create Date: 2025-03-13 14:47:53.875840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37598a4f00fb'
down_revision: Union[str, None] = 'e27c1a766c49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE roleenum AS ENUM ('USER', 'ADMIN')")
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'role',
               existing_type=sa.VARCHAR(),
               type_=sa.Enum('USER', 'ADMIN', name='roleenum'),
               existing_nullable=False,
               postgresql_using='role::roleenum')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'role',
               existing_type=sa.Enum('USER', 'ADMIN', name='roleenum'),
               type_=sa.VARCHAR(),
               existing_nullable=False)
    # ### end Alembic commands ###
