"""Clean slate - truncate all game-related tables

Revision ID: 017_clean_slate
Revises: 016_add_players_teams_fk
Create Date: 2026-09-01 11:00:00.000000

This migration:
1. Truncates all event-related tables (events, goals, cards, etc.)
2. Truncates all lineup tables
3. Truncates all games
4. Keeps teams and competitions for reference

Use this to reset data while keeping schema structure.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017_clean_slate'
down_revision = '016_add_players_teams_fk'
branch_labels = None
depends_on = None


def upgrade():
    """Truncate all game-related data"""
    
    # Disable FK checks temporarily
    op.execute('SET session_replication_role = replica')
    
    # ========================================================================
    # Truncate in reverse dependency order (deepest first)
    # ========================================================================
    
    # Events & event-related
    op.execute('TRUNCATE TABLE events CASCADE')
    op.execute('TRUNCATE TABLE goals CASCADE')
    op.execute('TRUNCATE TABLE card CASCADE')
    op.execute('TRUNCATE TABLE foul CASCADE')
    op.execute('TRUNCATE TABLE goalkick CASCADE')
    op.execute('TRUNCATE TABLE offside CASCADE')
    op.execute('TRUNCATE TABLE ball_in_play CASCADE')
    op.execute('TRUNCATE TABLE kickoff CASCADE')
    op.execute('TRUNCATE TABLE phase_of_play CASCADE')
    op.execute('TRUNCATE TABLE type_of_play CASCADE')
    op.execute('TRUNCATE TABLE setpieces CASCADE')
    
    # Game events
    op.execute('TRUNCATE TABLE game_goals CASCADE')
    op.execute('TRUNCATE TABLE game_cards CASCADE')
    op.execute('TRUNCATE TABLE game_score_evolution CASCADE')
    op.execute('TRUNCATE TABLE periods CASCADE')
    op.execute('TRUNCATE TABLE game_status CASCADE')
    
    # Fitness & analytics
    op.execute('TRUNCATE TABLE player_fitness_runs CASCADE')
    op.execute('TRUNCATE TABLE player_fitness_summary CASCADE')
    op.execute('TRUNCATE TABLE team_fitness_summary CASCADE')
    op.execute('TRUNCATE TABLE possession_collective CASCADE')
    op.execute('TRUNCATE TABLE individual_possession CASCADE')
    
    # Lineups
    op.execute('TRUNCATE TABLE lineup_players CASCADE')
    op.execute('TRUNCATE TABLE lineup_teams CASCADE')
    
    # Output files
    op.execute('TRUNCATE TABLE output_files CASCADE')
    
    # Scraping logs
    op.execute('TRUNCATE TABLE scraping_logs CASCADE')
    op.execute('TRUNCATE TABLE scraping_tasks CASCADE')
    
    # Main tables
    op.execute('TRUNCATE TABLE games CASCADE')
    op.execute('TRUNCATE TABLE players CASCADE')
    
    # Re-enable FK checks
    op.execute('SET session_replication_role = default')


def downgrade():
    """No downgrade - this is a one-way clean slate operation"""
    pass
