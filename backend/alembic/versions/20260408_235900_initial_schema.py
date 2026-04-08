"""
Initial versioned schema for LEVI-AI SQL persistence.
"""

from __future__ import annotations

from alembic import op

from backend.db.postgres import Base
import backend.db.models  # noqa: F401

# revision identifiers, used by Alembic.
revision = "20260408_235900"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
