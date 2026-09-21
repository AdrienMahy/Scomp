"""Add distance_covered and player_distance_covered tables with JSONB time_intervals

Revision ID: 032_add_distance_covered_tables
Revises: 031_add_stats_to_scraping_logs
Create Date: 2026-09-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '032_add_distance_covered_tables'
down_revision = '031_add_stats_to_scraping_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create team_distance_covered and player_distance_covered tables"""
    
    # Create team_distance_covered table
    op.create_table(
        'team_distance_covered',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('total_distance_m', sa.Float(), nullable=False),
        sa.Column('walking_m', sa.Float(), nullable=True),
        sa.Column('jogging_m', sa.Float(), nullable=True),
        sa.Column('moderated_intensity_m', sa.Float(), nullable=True),
        sa.Column('high_intensity_m', sa.Float(), nullable=True),
        sa.Column('sprint_m', sa.Float(), nullable=True),
        sa.Column('in_play_m', sa.Float(), nullable=True),
        sa.Column('out_of_play_m', sa.Float(), nullable=True),
        sa.Column('time_intervals', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_team_distance_covered_game_id'), 'team_distance_covered', ['game_id'], unique=False)
    op.create_index(op.f('ix_team_distance_covered_team_id'), 'team_distance_covered', ['team_id'], unique=False)
    op.create_index('ix_team_distance_covered_time_intervals', 'team_distance_covered', ['time_intervals'], postgresql_using='gin')
    
    # Create player_distance_covered table
    op.create_table(
        'player_distance_covered',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('game_id', sa.String(36), nullable=False),
        sa.Column('player_id', sa.String(36), nullable=False),
        sa.Column('team_id', sa.String(36), nullable=True),
        sa.Column('minutes_played', sa.Float(), nullable=True),
        sa.Column('total_distance_m', sa.Float(), nullable=False),
        sa.Column('distance_per_min_played_m', sa.Float(), nullable=True),
        sa.Column('walking_m', sa.Float(), nullable=True),
        sa.Column('jogging_m', sa.Float(), nullable=True),
        sa.Column('moderated_intensity_m', sa.Float(), nullable=True),
        sa.Column('high_intensity_m', sa.Float(), nullable=True),
        sa.Column('sprint_m', sa.Float(), nullable=True),
        sa.Column('in_play_m', sa.Float(), nullable=True),
        sa.Column('out_of_play_m', sa.Float(), nullable=True),
        sa.Column('time_intervals', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_player_distance_covered_game_id'), 'player_distance_covered', ['game_id'], unique=False)
    op.create_index(op.f('ix_player_distance_covered_player_id'), 'player_distance_covered', ['player_id'], unique=False)
    op.create_index(op.f('ix_player_distance_covered_team_id'), 'player_distance_covered', ['team_id'], unique=False)
    op.create_index('ix_player_distance_covered_game_player', 'player_distance_covered', ['game_id', 'player_id'], unique=False)
    op.create_index('ix_player_distance_covered_time_intervals', 'player_distance_covered', ['time_intervals'], postgresql_using='gin')


def downgrade() -> None:
    """Drop distance_covered and player_distance_covered tables"""
    
    # Drop indices
    op.drop_index('ix_player_distance_covered_time_intervals', table_name='player_distance_covered')
    op.drop_index('ix_player_distance_covered_game_player', table_name='player_distance_covered')
    op.drop_index(op.f('ix_player_distance_covered_team_id'), table_name='player_distance_covered')
    op.drop_index(op.f('ix_player_distance_covered_player_id'), table_name='player_distance_covered')
    op.drop_index(op.f('ix_player_distance_covered_game_id'), table_name='player_distance_covered')
    
    # Drop tables
    op.drop_table('player_distance_covered')
    
    op.drop_index('ix_team_distance_covered_time_intervals', table_name='team_distance_covered')
    op.drop_index(op.f('ix_team_distance_covered_team_id'), table_name='team_distance_covered')
    op.drop_index(op.f('ix_team_distance_covered_game_id'), table_name='team_distance_covered')
    
    op.drop_table('team_distance_covered')
