"""Create a view of corner kicks.

Revision ID: 20261012_020000
Revises: 20261012_010000
"""

from alembic import op


revision = "20261012_020000"
down_revision = "20261012_010000"
branch_labels = None
depends_on = None


VIEW_SQL = """
CREATE OR REPLACE VIEW v_corners AS
SELECT
    sp.id AS corner_id,
    sp.entity->>'sequence_id' AS sequence_id,
    sp.game_id,
    g.name AS game_name,
    COALESCE(g.round_name, g.round) AS round,
    sp.team_id,
    team.name AS team_name,
    sp.opponent_team_id,
    opponent.name AS opponent_team_name,
    COALESCE(sp.player_id, sp.actors->>'taker') AS taker_id,
    taker.name AS taker_name,
    sp.period_id AS period,
    sp.corner_kick->>'quarter' AS quarter,
    sp.spatial->>'side' AS side,
    CASE
        WHEN sp.corner_kick->>'short_corner' IN ('true', 'false')
        THEN (sp.corner_kick->>'short_corner')::boolean
    END AS short_corner,
    sp.corner_kick->>'outcome' AS outcome,
    CASE
        WHEN sp.corner_kick->>'goal_in_sequence' IN ('true', 'false')
        THEN (sp.corner_kick->>'goal_in_sequence')::boolean
    END AS goal_in_sequence
FROM setpieces AS sp
JOIN games AS g
    ON g.id = sp.game_id
LEFT JOIN teams AS team
    ON team.id = sp.team_id
LEFT JOIN teams AS opponent
    ON opponent.id = sp.opponent_team_id
LEFT JOIN players AS taker
    ON taker.id = COALESCE(sp.player_id, sp.actors->>'taker')
WHERE lower(trim(replace(sp.gata_display_name, '-', ' '))) = 'corner kick'
"""


def upgrade() -> None:
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_corners")
