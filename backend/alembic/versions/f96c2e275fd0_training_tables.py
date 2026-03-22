"""training_tables

Revision ID: f96c2e275fd0
Revises: c05c8c32cadb
Create Date: 2026-03-23 01:37:45.700303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f96c2e275fd0'
down_revision: Union[str, Sequence[str], None] = 'c05c8c32cadb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('training_data',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('bot_response', sa.Text(), nullable=False),
        sa.Column('mood', sa.String(), default='philosophical'),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('fingerprint', sa.String(), unique=True, nullable=True),
        sa.Column('is_exported', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_table('prompt_performance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('variant_idx', sa.Integer(), unique=True),
        sa.Column('avg_score', sa.Float(), default=3.0),
        sa.Column('sample_count', sa.Integer(), default=0),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_table('model_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.String(), unique=True),
        sa.Column('model_id', sa.String(), unique=True),
        sa.Column('training_samples', sa.Integer(), default=0),
        sa.Column('eval_score', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_table('training_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.String(), unique=True),
        sa.Column('file_id', sa.String(), nullable=True),
        sa.Column('training_samples', sa.Integer(), default=0),
        sa.Column('status', sa.String(), default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table('response_feedback',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('training_data_id', sa.Integer(), sa.ForeignKey('training_data.id'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('message_hash', sa.String(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('feedback_type', sa.String(), default='star'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )


def downgrade() -> None:
    """Downgrade schema."""
    for t in ['response_feedback','training_jobs','model_versions','prompt_performance','training_data']:
        op.drop_table(t)
