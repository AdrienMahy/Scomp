"""Clean slate - truncate everything including teams

Revision ID: 018_clean_slate_with_teams
Revises: 017_clean_slate
Create Date: 2026-09-01 11:05:00.000000

This migration:
1. Truncates all event-related tables
2. Truncates games, lineups, players
3. Truncates TEAMS (fresh start)
4. Keeps only competitions and seasons

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '018_clean_slate_with_teams'
down_revision = '017_clean_slate'
branch_labels = None
depends_on = None


def upgrade():
    """Truncate all data including teams"""
    
    # Disable FK checks temporarily
    op.execute('SET session_replication_role = replica')
    
    # ========================================================================
    # Truncate everything except competitions & seasons
    # ========================================================================
    
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
    op.execute('TRUNCATE TABLE game_goals CASCADE')
    op.execute('TRUNCATE TABLE game_cards CASCADE')
    op.execute('TRUNCATE TABLE game_score_evolution CASCADE')
    op.execute('TRUNCATE TABLE periods CASCADE')
    op.execute('TRUNCATE TABLE game_status CASCADE')
    op.execute('TRUNCATE TABLE player_fitness_runs CASCADE')
    op.execute('TRUNCATE TABLE player_fitness_summary CASCADE')
    op.execute('TRUNCATE TABLE team_fitness_summary CASCADE')
    op.execute('TRUNCATE TABLE possession_collective CASCADE')
    op.execute('TRUNCATE TABLE individual_possession CASCADE')
    op.execute('TRUNCATE TABLE lineup_players CASCADE')
    op.execute('TRUNCATE TABLE lineup_teams CASCADE')
    op.execute('TRUNCATE TABLE output_files CASCADE')
    op.execute('TRUNCATE TABLE scraping_logs CASCADE')
    op.execute('TRUNCATE TABLE scraping_tasks CASCADE')
    op.execute('TRUNCATE TABLE games CASCADE')
    op.execute('TRUNCATE TABLE players CASCADE')
    op.execute('TRUNCATE TABLE teams CASCADE')
    
    # Re-enable FK checks
    op.execute('SET session_replication_role = default')


def downgrade():
    """No downgrade - this is a one-way clean slate operation"""
    pass
