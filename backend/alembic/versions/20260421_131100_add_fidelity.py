"""
Add fidelity column to MissionMetric.
Revision ID: 20260421_131100
Revises: 20260408_235900
"""

from alembic import op
import sqlalchemy as sa

revision = '20260421_131100'
down_revision = '20260408_235900'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('mission_metrics', sa.Column('fidelity', sa.Float(), nullable=True, server_default='1.0'))

def downgrade():
    op.drop_column('mission_metrics', 'fidelity')
