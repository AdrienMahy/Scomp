"""Enhance v_periods view to extract team_id, game_id, period_id, value, coef

Revision ID: 20260917_142000
Revises: 20260917_085500
Create Date: 2026-09-17 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260917_142000'
down_revision = '20260917_085500'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop and recreate v_periods view with enhanced columns."""
    op.execute("""
        DROP VIEW IF EXISTS v_periods CASCADE;
        
        CREATE VIEW v_periods AS
        WITH period_teams AS (
            -- Extract HOME team (index 0)
            SELECT 
                p.id as period_id,
                p.game_id as game_id,
                p.period_id as period,
                g.name as game,
                (p.direction->0->>'team_id') as team_id,
                ht.name as team,
                (p.direction->0->>'value') as value,
                (p.direction->0->>'coef')::INTEGER as coef
            FROM periods p
            JOIN games g ON p.game_id = g.id
            JOIN teams ht ON (p.direction->0->>'team_id') = ht.id
            WHERE p.direction IS NOT NULL
            UNION ALL
            -- Extract AWAY team (index 1)
            SELECT 
                p.id,
                p.game_id,
                p.period_id,
                g.name,
                (p.direction->1->>'team_id'),
                at.name,
                (p.direction->1->>'value'),
                (p.direction->1->>'coef')::INTEGER
            FROM periods p
            JOIN games g ON p.game_id = g.id
            JOIN teams at ON (p.direction->1->>'team_id') = at.id
            WHERE p.direction IS NOT NULL
        )
        SELECT 
            period_id,
            game_id,
            period,
            game,
            team_id,
            team,
            value,
            coef
        FROM period_teams
        ORDER BY game_id, period, team_id;
    """)


def downgrade() -> None:
    """Restore previous v_periods view."""
    op.execute("""
        DROP VIEW IF EXISTS v_periods CASCADE;
        
        CREATE VIEW v_periods AS
        WITH period_teams AS (
            -- Extract HOME team (index 0) coefficient
            SELECT 
                p.period_id as period,
                g.name as game,
                ht.name as team,
                (p.direction->0->'team'->>'coef')::INTEGER as coef
            FROM periods p
            JOIN games g ON p.game_id = g.id
            JOIN teams ht ON g.home_team_id = ht.id
            WHERE p.direction IS NOT NULL
            UNION ALL
            -- Extract AWAY team (index 1) coefficient
            SELECT 
                p.period_id,
                g.name,
                at.name,
                (p.direction->1->'team'->>'coef')::INTEGER
            FROM periods p
            JOIN games g ON p.game_id = g.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE p.direction IS NOT NULL
        )
        SELECT 
            coef,
            game,
            team,
            period
        FROM period_teams
        ORDER BY game, period, team;
    """)
