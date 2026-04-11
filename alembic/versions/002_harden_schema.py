# alembic/versions/002_harden_schema.py
"""harden schema

Revision ID: 002
Revises: 001
Create Date: 2026-04-11 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Update user_profiles (remove JSON columns, add role/archetype etc)
    op.add_column('user_profiles', sa.Column('role', sa.String(32), server_default='user'))
    op.add_column('user_profiles', sa.Column('response_style', sa.String(32), server_default='balanced'))
    op.add_column('user_profiles', sa.Column('persona_archetype', sa.String(64), server_default='philosophical'))
    op.add_column('user_profiles', sa.Column('avg_rating', sa.Float(), server_default='3.0'))
    op.add_column('user_profiles', sa.Column('total_interactions', sa.Integer(), server_default='0'))
    # JSON traits/preferences were in 001, we'll keep them or migrate to tables
    # For now, let's just add the tables as per models.py

    # 2. User Traits Table
    op.create_table(
        'user_traits',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(36), index=True),
        sa.Column('trait', sa.String(255), nullable=False),
        sa.Column('weight', sa.Float(), server_default='0.5'),
        sa.Column('evidence_count', sa.Integer(), server_default='1'),
        sa.Column('crystallized_at', sa.DateTime(), server_default=sa.func.now())
    )

    # 3. User Preferences Table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(36), index=True),
        sa.Column('category', sa.String(64)),
        sa.Column('value', sa.String(255)),
        sa.Column('resonance_score', sa.Float(), server_default='0.5')
    )

    # 4. User Facts Table
    op.create_table(
        'user_facts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(36), index=True),
        sa.Column('fact', sa.Text(), nullable=False),
        sa.Column('category', sa.String(64), server_default='general'),
        sa.Column('importance', sa.Float(), server_default='0.5'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), server_default='false')
    )

    # 5. Mission Metrics Table
    op.create_table(
        'mission_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mission_id', sa.String(36), index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(36), index=True),
        sa.Column('intent', sa.String(64)),
        sa.Column('status', sa.String(32)),
        sa.Column('token_count', sa.Integer(), server_default='0'),
        sa.Column('cost_usd', sa.Float(), server_default='0.0'),
        sa.Column('latency_ms', sa.Float(), server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # 6. Custom Agents Table
    op.create_table(
        'custom_agents',
        sa.Column('agent_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('config_json', postgresql.JSON()),
        sa.Column('is_public', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # 7. Marketplace Agents Table
    op.create_table(
        'marketplace_agents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('agent_id', sa.String(36), index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('creator_id', sa.String(36)),
        sa.Column('description', sa.Text()),
        sa.Column('price_units', sa.Integer(), server_default='0'),
        sa.Column('category', sa.String(64)),
        sa.Column('downloads', sa.Integer(), server_default='0'),
        sa.Column('rating', sa.Float(), server_default='5.0'),
        sa.Column('config_json', postgresql.JSON()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # 8. Missions Aborted Table (Resilience)
    op.create_table(
        'missions_aborted',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mission_id', sa.String(36), sa.ForeignKey('missions.id'), unique=True, index=True),
        sa.Column('user_id', sa.String(36), index=True),
        sa.Column('frozen_dag', postgresql.JSON()),
        sa.Column('wave_index', sa.Integer(), server_default='0'),
        sa.Column('error_node_id', sa.String(128)),
        sa.Column('payload', postgresql.JSON()),
        sa.Column('aborted_at', sa.DateTime(), server_default=sa.func.now())
    )

    # 9. Graduated Rules Table
    op.create_table(
        'graduated_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('task_pattern', sa.Text(), unique=True, index=True, nullable=False),
        sa.Column('result_data', postgresql.JSON(), nullable=False),
        sa.Column('fidelity_score', sa.Float(), nullable=False),
        sa.Column('uses_count', sa.Integer(), server_default='0'),
        sa.Column('is_stable', sa.Boolean(), server_default='false'),
        sa.Column('last_validated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # 10. Fragility Index Table
    op.create_table(
        'fragility_index',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(36), index=True),
        sa.Column('domain', sa.String(64), index=True),
        sa.Column('failure_count', sa.Integer(), server_default='0'),
        sa.Column('success_streak', sa.Integer(), server_default='0'),
        sa.Column('weighted_fidelity', sa.Float(), server_default='1.0'),
        sa.Column('fragility_score', sa.Float(), server_default='0.0'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now())
    )

    # 11. Creation Jobs Table
    op.create_table(
        'creation_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.String(36), unique=True, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(36), index=True),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('result_url', sa.String(512)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime())
    )

    # 12. Cognitive Usage Table
    op.create_table(
        'cognitive_usage',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mission_id', sa.String(36), sa.ForeignKey('missions.id'), index=True),
        sa.Column('user_id', sa.String(36), index=True),
        sa.Column('agent', sa.String(64)),
        sa.Column('prompt_tokens', sa.Integer(), server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), server_default='0'),
        sa.Column('latency_ms', sa.Integer(), server_default='0'),
        sa.Column('cu_cost', sa.Float(), server_default='0.0'),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('cognitive_usage')
    op.drop_table('creation_jobs')
    op.drop_table('fragility_index')
    op.drop_table('graduated_rules')
    op.drop_table('missions_aborted')
    op.drop_table('marketplace_agents')
    op.drop_table('custom_agents')
    op.drop_table('mission_metrics')
    op.drop_table('user_facts')
    op.drop_table('user_preferences')
    op.drop_table('user_traits')
    op.drop_column('user_profiles', 'total_interactions')
    op.drop_column('user_profiles', 'avg_rating')
    op.drop_column('user_profiles', 'persona_archetype')
    op.drop_column('user_profiles', 'response_style')
    op.drop_column('user_profiles', 'role')
