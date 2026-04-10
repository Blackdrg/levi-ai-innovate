# alembic/versions/001_initial_schema.py
"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-04-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # User profiles
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('traits', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('idx_tenant_email', 'tenant_id', 'email'),
    )

    # Missions ledger
    op.create_table(
        'missions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.id'), nullable=False),
        sa.Column('objective', sa.Text, nullable=False),
        sa.Column('status', sa.String(32), default='CREATED'),
        sa.Column('frozen_dag', postgresql.JSON, nullable=True),
        sa.Column('fidelity_score', sa.Float, default=0.0),
        sa.Column('wave_index', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('idx_tenant_status', 'tenant_id', 'status'),
        sa.Index('idx_created_at', 'created_at'),
    )

    # Interaction log (immutable, partitioned)
    op.create_table(
        'interaction_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('mission_id', sa.String(36), sa.ForeignKey('missions.id'), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('data', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Index('idx_mission_created', 'mission_id', 'created_at'),
    )

    # Audit log (monthly partitioned)
    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=False),
        sa.Column('details', postgresql.JSON, nullable=True),
        sa.Column('integrity_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Index('idx_audit_tenant_date', 'tenant_id', 'created_at'),
    )

    # Credits ledger
    op.create_table(
        'user_credits',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.id'), nullable=False),
        sa.Column('balance', sa.Numeric(10, 2), default=0.0),
        sa.Column('tier', sa.String(32), default='free'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Index('idx_user_id', 'user_id'),
    )

def downgrade():
    op.drop_table('user_credits')
    op.drop_table('audit_log')
    op.drop_table('interaction_log')
    op.drop_table('missions')
    op.drop_table('user_profiles')
