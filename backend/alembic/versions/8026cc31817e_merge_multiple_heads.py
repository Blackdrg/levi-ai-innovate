"""merge multiple heads

Revision ID: 8026cc31817e
Revises: 48dff1cc8645, dd5e6f6a7b8c
Create Date: 2026-03-25 14:53:18.297166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8026cc31817e'
down_revision: Union[str, Sequence[str], None] = ('48dff1cc8645', 'dd5e6f6a7b8c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
