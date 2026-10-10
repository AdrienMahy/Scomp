"""Add a two-row-per-match game information view.

Revision ID: 20261008_120000
Revises: 20261008_110000
"""

from alembic import op


revision = "20261008_120000"
down_revision = "20261008_110000"
branch_labels = None
depends_on = None


VIEW_SQL = """
CREATE VIEW v_game_information AS
SELECT
    g.id,
    g.name,
    COALESCE(g.round_name, g.round) AS round,
    current_team.name AS team_name,
    home_team.name AS home_team_name,
    away_team.name AS away_team_name,
    CASE
        WHEN g.home_score IS NOT NULL AND g.away_score IS NOT NULL
        THEN format('%s - %s', g.home_score, g.away_score)
        ELSE NULL
    END AS score,
    g.starts_at::date AS game_date
FROM games AS g
LEFT JOIN teams AS home_team ON home_team.id = g.home_team_id
LEFT JOIN teams AS away_team ON away_team.id = g.away_team_id
CROSS JOIN LATERAL (
    VALUES (g.home_team_id), (g.away_team_id)
) AS match_teams(team_id)
LEFT JOIN teams AS current_team ON current_team.id = match_teams.team_id
"""


def upgrade() -> None:
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW v_game_information")
