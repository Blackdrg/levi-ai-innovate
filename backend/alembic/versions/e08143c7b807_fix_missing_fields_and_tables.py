# pyright: reportMissingImports=false
"""fix_missing_fields_and_tables

Revision ID: e08143c7b807
Revises: f96c2e275fd0
Create Date: 2026-03-23 13:15:01.813577

"""
from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore


# revision identifiers, used by Alembic.
revision: str = 'e08143c7b807'
down_revision: Union[str, Sequence[str], None] = 'f96c2e275fd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns to users table
    op.add_column('users', sa.Column('is_verified', sa.Integer(), server_default='0', nullable=True))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('verification_token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('reset_password_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_password_token_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Create payment_events table
    op.create_table('payment_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.String(length=100), nullable=False),
        sa.Column('order_id', sa.String(length=100), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_events_id'), 'payment_events', ['id'], unique=False)
    op.create_index(op.f('ix_payment_events_payment_id'), 'payment_events', ['payment_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_payment_events_payment_id'), table_name='payment_events')
    op.drop_index(op.f('ix_payment_events_id'), table_name='payment_events')
    op.drop_table('payment_events')
    
    # SQLite doesn't support dropping columns easily in older versions, 
    # but for completeness we include them. 
    # op.drop_column('users', 'reset_password_token_expires_at')
    # op.drop_column('users', 'reset_password_token')
    # op.drop_column('users', 'verification_token_expires_at')
    # op.drop_column('users', 'verification_token')
    # op.drop_column('users', 'is_verified')
    pass
