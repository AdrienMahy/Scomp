"""Add fitness entities tables with hybrid schema

Revision ID: 002_add_fitness_entities
Revises: 001_hybrid_events_schema
Create Date: 2026-08-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '002_add_fitness_entities'
down_revision = '001_hybrid_events_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Create player_fitness_runs, player_fitness_summary, and team_fitness_summary tables"""
    
    # ========================================================================
    # PLAYER_FITNESS_RUNS TABLE
    # ========================================================================
    op.create_table(
        'player_fitness_runs',
        
        # === PRIMARY IDs ===
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        
        # === ACTOR IDs (Foreign Keys) ===
        sa.Column('player_id', sa.String(50), nullable=False, index=True),
        sa.Column('team_id', sa.String(50), nullable=False, index=True),
        sa.Column('opponent_team_id', sa.String(50), nullable=False),
        
        # === EVENT REFERENCES (Foreign Keys to Event Tables - CRITICAL) ===
        sa.Column('possession_id', sa.String(50), nullable=True, index=True),
        sa.Column('phase_of_play_id', sa.String(50), nullable=True, index=True),
        sa.Column('type_of_play_id', sa.String(50), nullable=True, index=True),
        sa.Column('individual_possession_id', sa.String(50), nullable=True, index=True),
        
        # === TIMING METRICS (5 columns) ===
        sa.Column('start_time_s', sa.Float(), nullable=False),
        sa.Column('end_time_s', sa.Float(), nullable=False),
        sa.Column('duration_s', sa.Float(), nullable=False),
        sa.Column('start_frame', sa.Integer(), nullable=True),
        sa.Column('end_frame', sa.Integer(), nullable=True),
        
        # === DISTANCE METRICS (3 columns) ===
        sa.Column('distance_m', sa.Float(), nullable=False),
        sa.Column('high_speed_distance_m', sa.Float(), nullable=True),
        sa.Column('sprint_distance_m', sa.Float(), nullable=True),
        
        # === SPEED METRICS (5 columns) ===
        sa.Column('average_speed', sa.Float(), nullable=True),
        sa.Column('peak_speed', sa.Float(), nullable=True),
        sa.Column('high_speed_duration', sa.Float(), nullable=True),
        sa.Column('sprint_duration', sa.Float(), nullable=True),
        sa.Column('time_to_peak_speed', sa.Float(), nullable=True),
        
        # === ACCELERATION METRICS (4 columns) ===
        sa.Column('acceleration_at_start', sa.Float(), nullable=True),
        sa.Column('peak_acceleration', sa.Float(), nullable=True),
        sa.Column('peak_deceleration', sa.Float(), nullable=True),
        sa.Column('acceleration_intensity', sa.Integer(), nullable=True),
        sa.Column('acceleration_intensity_level', sa.String(50), nullable=True),
        
        # === TACTICAL CONTEXT (5 columns) ===
        sa.Column('context', sa.String(50), nullable=True),
        sa.Column('direction', sa.String(50), nullable=True),
        sa.Column('phase_of_play_label', sa.String(100), nullable=True),
        sa.Column('play_label', sa.String(100), nullable=True),
        sa.Column('possession_label', sa.String(50), nullable=True),
        
        # === SPATIAL POSITIONING (8 columns) ===
        sa.Column('start_x', sa.Float(), nullable=True),
        sa.Column('start_y', sa.Float(), nullable=True),
        sa.Column('end_x', sa.Float(), nullable=True),
        sa.Column('end_y', sa.Float(), nullable=True),
        sa.Column('start_third', sa.String(50), nullable=True),
        sa.Column('end_third', sa.String(50), nullable=True),
        sa.Column('start_channel', sa.String(50), nullable=True),
        sa.Column('end_channel', sa.String(50), nullable=True),
        
        # === BOOLEAN CLASSIFICATIONS (5 columns) ===
        sa.Column('high_speed_run', sa.Boolean(), default=False, nullable=True),
        sa.Column('is_receiving_run', sa.Boolean(), default=False, nullable=True),
        sa.Column('sprint', sa.Boolean(), default=False, nullable=True),
        sa.Column('run_with_ball', sa.Boolean(), default=False, nullable=True),
        sa.Column('on_ball_run', sa.Boolean(), default=False, nullable=True),
        
        # === BOX & ZONE ENTRIES (5 columns) ===
        sa.Column('defensive_box_entry', sa.Boolean(), default=False, nullable=True),
        sa.Column('offensive_box_entry', sa.Boolean(), default=False, nullable=True),
        sa.Column('defensive_third_entry', sa.Boolean(), default=False, nullable=True),
        sa.Column('offensive_third_entry', sa.Boolean(), default=False, nullable=True),
        sa.Column('functional_start_zone', sa.String(100), nullable=True),
        
        # === JSONB METADATA ===
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # === PRIMARY KEY ===
        sa.PrimaryKeyConstraint('id'),
        
        # === FOREIGN KEYS ===
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opponent_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['possession_id'], ['possession_collective.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['phase_of_play_id'], ['phase_of_play.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['type_of_play_id'], ['type_of_play.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['individual_possession_id'], ['individual_possession.id'], ondelete='SET NULL'),
    )
    
    # === INDEXES for player_fitness_runs ===
    op.create_index('idx_pfr_game_period', 'player_fitness_runs', ['game_id', 'period_id'])
    op.create_index('idx_pfr_player', 'player_fitness_runs', ['player_id'])
    op.create_index('idx_pfr_team', 'player_fitness_runs', ['team_id'])
    op.create_index('idx_pfr_possession', 'player_fitness_runs', ['possession_id'])
    op.create_index('idx_pfr_phase_of_play', 'player_fitness_runs', ['phase_of_play_id'])
    op.create_index('idx_pfr_type_of_play', 'player_fitness_runs', ['type_of_play_id'])
    op.create_index('idx_pfr_individual_possession', 'player_fitness_runs', ['individual_possession_id'])
    op.create_index('idx_pfr_context', 'player_fitness_runs', ['context'])
    op.create_index('idx_pfr_direction', 'player_fitness_runs', ['direction'])
    op.create_index('idx_pfr_acceleration_level', 'player_fitness_runs', ['acceleration_intensity_level'])
    op.create_index('idx_pfr_context_phase', 'player_fitness_runs', ['context', 'phase_of_play_id'])
    op.create_index('idx_pfr_team_phase', 'player_fitness_runs', ['team_id', 'phase_of_play_id'])
    op.create_index('idx_pfr_possession_duration', 'player_fitness_runs', ['possession_id', 'duration_s'])
    op.create_index('idx_pfr_phase_distance', 'player_fitness_runs', ['phase_of_play_id', 'distance_m'])
    op.create_index('idx_pfr_metadata_gin', 'player_fitness_runs', ['metadata_json'], postgresql_using='gin')
    
    
    # ========================================================================
    # PLAYER_FITNESS_SUMMARY TABLE (Optional aggregation)
    # ========================================================================
    op.create_table(
        'player_fitness_summary',
        
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('player_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        
        # Aggregated metrics
        sa.Column('total_runs', sa.Integer(), default=0, nullable=True),
        sa.Column('total_distance_m', sa.Float(), default=0.0, nullable=True),
        sa.Column('total_high_speed_distance_m', sa.Float(), default=0.0, nullable=True),
        sa.Column('total_sprint_distance_m', sa.Float(), default=0.0, nullable=True),
        sa.Column('average_run_speed_ms', sa.Float(), nullable=True),
        sa.Column('peak_speed_ms', sa.Float(), nullable=True),
        
        # Classification counts
        sa.Column('high_speed_run_count', sa.Integer(), default=0, nullable=True),
        sa.Column('sprint_count', sa.Integer(), default=0, nullable=True),
        sa.Column('receiving_run_count', sa.Integer(), default=0, nullable=True),
        
        # Context distribution
        sa.Column('offensive_runs', sa.Integer(), default=0, nullable=True),
        sa.Column('defensive_runs', sa.Integer(), default=0, nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_pfs_game', 'player_fitness_summary', ['game_id'])
    op.create_index('idx_pfs_player', 'player_fitness_summary', ['player_id'])
    op.create_index('idx_pfs_team', 'player_fitness_summary', ['team_id'])
    op.create_index('idx_pfs_game_player', 'player_fitness_summary', ['game_id', 'player_id'])
    
    
    # ========================================================================
    # TEAM_FITNESS_SUMMARY TABLE (Optional aggregation)
    # ========================================================================
    op.create_table(
        'team_fitness_summary',
        
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        
        # Aggregated metrics
        sa.Column('total_runs', sa.Integer(), default=0, nullable=True),
        sa.Column('total_distance_m', sa.Float(), default=0.0, nullable=True),
        sa.Column('total_high_speed_distance_m', sa.Float(), default=0.0, nullable=True),
        sa.Column('total_sprint_distance_m', sa.Float(), default=0.0, nullable=True),
        sa.Column('average_team_speed_ms', sa.Float(), nullable=True),
        
        # Players involved
        sa.Column('players_tracked', sa.Integer(), default=0, nullable=True),
        
        # Context distribution
        sa.Column('offensive_runs', sa.Integer(), default=0, nullable=True),
        sa.Column('defensive_runs', sa.Integer(), default=0, nullable=True),
        
        # Performance by phase
        sa.Column('average_runs_per_phase', sa.Float(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_tfs_game', 'team_fitness_summary', ['game_id'])
    op.create_index('idx_tfs_team', 'team_fitness_summary', ['team_id'])
    op.create_index('idx_tfs_game_team', 'team_fitness_summary', ['game_id', 'team_id'])


def downgrade():
    """Drop all fitness tables"""
    
    op.drop_index('idx_tfs_game_team', table_name='team_fitness_summary')
    op.drop_index('idx_tfs_team', table_name='team_fitness_summary')
    op.drop_index('idx_tfs_game', table_name='team_fitness_summary')
    op.drop_table('team_fitness_summary')
    
    op.drop_index('idx_pfs_game_player', table_name='player_fitness_summary')
    op.drop_index('idx_pfs_team', table_name='player_fitness_summary')
    op.drop_index('idx_pfs_player', table_name='player_fitness_summary')
    op.drop_index('idx_pfs_game', table_name='player_fitness_summary')
    op.drop_table('player_fitness_summary')
    
    op.drop_index('idx_pfr_metadata_gin', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_phase_distance', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_possession_duration', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_team_phase', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_context_phase', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_acceleration_level', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_direction', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_context', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_individual_possession', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_type_of_play', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_phase_of_play', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_possession', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_team', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_player', table_name='player_fitness_runs')
    op.drop_index('idx_pfr_game_period', table_name='player_fitness_runs')
    op.drop_table('player_fitness_runs')
