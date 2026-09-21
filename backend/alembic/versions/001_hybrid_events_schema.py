"""Create hybrid schema event tables

Revision ID: 001_hybrid_events_schema
Revises: 000_base_tables
Create Date: 2026-08-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001_hybrid_events_schema'
down_revision = '000_base_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create all event tables with hybrid schema (critical columns + JSONB)"""
    
    # ========================================================================
    # EVENTS TABLE - Main table with 12 critical columns + 17 JSONB sections
    # ========================================================================
    op.create_table(
        'events',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        
        # Critical columns (BTREE indexed)
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('player_id', sa.String(50), nullable=True, index=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('opponent_team_id', sa.String(50), nullable=True, index=True),
        sa.Column('targeted_player_id', sa.String(50), nullable=True),
        sa.Column('goalkeeper_id', sa.String(50), nullable=True),
        sa.Column('expected_defender_at_arrival_id', sa.String(50), nullable=True),
        sa.Column('previous_passer_id', sa.String(50), nullable=True),
        sa.Column('possession_id', sa.String(50), nullable=True, index=True),
        sa.Column('type_of_play_id', sa.String(50), nullable=True, index=True),
        sa.Column('phase_of_play_id', sa.String(50), nullable=True, index=True),
        sa.Column('individual_possession_id', sa.String(50), nullable=True, index=True),
        
        # JSONB columns
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('phase', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('receiver', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('channel', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('adds', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('pass_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('custom', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cross', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('shot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('boxentry', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('finalthirdentry', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('clearance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('pressure', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('receivingrun', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['opponent_team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['targeted_player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['goalkeeper_id'], ['players.id']),
        sa.ForeignKeyConstraint(['expected_defender_at_arrival_id'], ['players.id']),
        sa.ForeignKeyConstraint(['previous_passer_id'], ['players.id']),
    )
    
    # Create composite indices
    op.create_index('idx_events_game_period', 'events', ['game_id', 'period_id'])
    op.create_index('idx_events_team_period', 'events', ['team_id', 'period_id'])
    op.create_index('idx_events_possession', 'events', ['possession_id'])
    op.create_index('idx_events_phase_jointure', 'events', ['phase_of_play_id', 'type_of_play_id'])
    op.create_index('idx_events_entity_gin', 'events', ['entity'], postgresql_using='gin')
    op.create_index('idx_events_spatial_gin', 'events', ['spatial'], postgresql_using='gin')
    op.create_index('idx_events_actors_gin', 'events', ['actors'], postgresql_using='gin')
    op.create_index('idx_events_pass_gin', 'events', ['pass_data'], postgresql_using='gin')
    op.create_index('idx_events_shot_gin', 'events', ['shot'], postgresql_using='gin')
    
    # ========================================================================
    # BALL_IN_PLAY TABLE
    # ========================================================================
    op.create_table(
        'ball_in_play',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_bip_game_period', 'ball_in_play', ['game_id', 'period_id'])
    
    # ========================================================================
    # CARD TABLE
    # ========================================================================
    op.create_table(
        'card',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('player_id', sa.String(50), nullable=True, index=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('card', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
    )
    op.create_index('idx_card_game_period', 'card', ['game_id', 'period_id'])
    op.create_index('idx_card_player', 'card', ['player_id'])
    
    # ========================================================================
    # FOUL TABLE
    # ========================================================================
    op.create_table(
        'foul',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('player_id', sa.String(50), nullable=True, index=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('foul', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
    )
    op.create_index('idx_foul_game_period', 'foul', ['game_id', 'period_id'])
    op.create_index('idx_foul_player', 'foul', ['player_id'])
    
    # ========================================================================
    # GOALKICK TABLE
    # ========================================================================
    op.create_table(
        'goalkick',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('goalkeeper_id', sa.String(50), nullable=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['goalkeeper_id'], ['players.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
    )
    op.create_index('idx_gk_game_period', 'goalkick', ['game_id', 'period_id'])
    
    # ========================================================================
    # GOALS TABLE
    # ========================================================================
    op.create_table(
        'goals',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('player_id', sa.String(50), nullable=True, index=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('shot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
    )
    op.create_index('idx_goals_game_period', 'goals', ['game_id', 'period_id'])
    op.create_index('idx_goals_player', 'goals', ['player_id'])
    op.create_index('idx_goals_team', 'goals', ['team_id'])
    
    # ========================================================================
    # INDIVIDUAL_POSSESSION TABLE
    # ========================================================================
    op.create_table(
        'individual_possession',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('player_id', sa.String(50), nullable=True, index=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('phase', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
    )
    op.create_index('idx_indposs_game_period', 'individual_possession', ['game_id', 'period_id'])
    op.create_index('idx_indposs_player', 'individual_possession', ['player_id'])
    
    # ========================================================================
    # KICKOFF TABLE
    # ========================================================================
    op.create_table(
        'kickoff',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_kickoff_game_period', 'kickoff', ['game_id', 'period_id'])
    
    # ========================================================================
    # OFFSIDE TABLE
    # ========================================================================
    op.create_table(
        'offside',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('player_id', sa.String(50), nullable=True, index=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
    )
    op.create_index('idx_offside_game_period', 'offside', ['game_id', 'period_id'])
    op.create_index('idx_offside_player', 'offside', ['player_id'])
    
    # ========================================================================
    # PHASE_OF_PLAY TABLE
    # ========================================================================
    op.create_table(
        'phase_of_play',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('opponent_team_id', sa.String(50), nullable=True),
        sa.Column('type_of_play_id', sa.String(50), nullable=True, index=True),
        sa.Column('starting_individual_possession_id', sa.String(50), nullable=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('phase', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['opponent_team_id'], ['teams.id']),
    )
    op.create_index('idx_phase_game_period', 'phase_of_play', ['game_id', 'period_id'])
    op.create_index('idx_phase_team', 'phase_of_play', ['team_id'])
    op.create_index('idx_phase_type', 'phase_of_play', ['type_of_play_id'])
    
    # ========================================================================
    # POSSESSION_COLLECTIVE TABLE
    # ========================================================================
    op.create_table(
        'possession_collective',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('team_id', sa.String(50), nullable=True, index=True),
        sa.Column('opponent_team_id', sa.String(50), nullable=True),
        sa.Column('ball_in_play_id', sa.String(50), nullable=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('phase', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('possession', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['opponent_team_id'], ['teams.id']),
    )
    op.create_index('idx_poss_game_period', 'possession_collective', ['game_id', 'period_id'])
    op.create_index('idx_poss_team', 'possession_collective', ['team_id'])
    
    # ========================================================================
    # SETPIECES TABLE
    # ========================================================================
    op.create_table(
        'setpieces',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('setpieces', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_setpiece_game_period', 'setpieces', ['game_id', 'period_id'])
    
    # ========================================================================
    # TYPE_OF_PLAY TABLE
    # ========================================================================
    op.create_table(
        'type_of_play',
        sa.Column('id', sa.String(50), default=uuid.uuid4, nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True, index=True),
        sa.Column('entity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('time', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('spatial', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('type_of_play', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_top_game_period', 'type_of_play', ['game_id', 'period_id'])


def downgrade():
    """Drop all event tables"""
    
    tables = [
        'type_of_play',
        'setpieces',
        'possession_collective',
        'phase_of_play',
        'offside',
        'kickoff',
        'individual_possession',
        'goals',
        'goalkick',
        'foul',
        'card',
        'ball_in_play',
        'events',
    ]
    
    for table in tables:
        op.drop_table(table)
