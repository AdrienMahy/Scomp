"""Add automation_configurations table"""
from alembic import op
import sqlalchemy as sa


revision = "20260921_000000"
down_revision = "20260919_110000"
branch_labels = None
depends_on = None


def upgrade():
    """Create automation_configurations table"""
    op.create_table(
        'automation_configurations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1024), nullable=True),
        sa.Column('competition_id', sa.String(50), nullable=False),
        sa.Column('competition_name', sa.String(255), nullable=False),
        sa.Column('season_id', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(50), server_default='sportsdynamics', nullable=False),
        sa.Column('scrape_interval_minutes', sa.Integer(), server_default='20', nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('look_ahead_days', sa.Integer(), server_default='7', nullable=False),
        sa.Column('look_back_days', sa.Integer(), server_default='1', nullable=False),
        sa.Column('live_game_window_minutes', sa.Integer(), server_default='120', nullable=False),
        sa.Column('task_timeout_seconds', sa.Integer(), server_default='1800', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_configurations_competition_id'), 'automation_configurations', ['competition_id'], unique=False)
    op.create_index(op.f('ix_automation_configurations_enabled'), 'automation_configurations', ['enabled'], unique=False)


def downgrade():
    """Drop automation_configurations table"""
    op.drop_index(op.f('ix_automation_configurations_enabled'), table_name='automation_configurations')
    op.drop_index(op.f('ix_automation_configurations_competition_id'), table_name='automation_configurations')
    op.drop_table('automation_configurations')
