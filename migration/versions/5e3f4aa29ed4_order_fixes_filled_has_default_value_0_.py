"""Order fixes. filled has default value 0 now

Revision ID: 5e3f4aa29ed4
Revises: afd99f1053f7
Create Date: 2025-04-03 15:57:10.917145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e3f4aa29ed4'
down_revision: Union[str, None] = 'afd99f1053f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('orders', 'filled',
                    existing_type=sa.INTEGER(),
                    server_default='0',
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('orders', 'filled',
                    server_default=None,
                    nullable=True)
