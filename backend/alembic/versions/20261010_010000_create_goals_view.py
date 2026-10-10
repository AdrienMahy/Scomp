"""Create a reporting view for canonical goals.

Revision ID: 20261010_010000
Revises: 20261010_000000
"""

from alembic import op


revision = "20261010_010000"
down_revision = "20261010_000000"
branch_labels = None
depends_on = None


VIEW_SQL = """
CREATE OR REPLACE VIEW v_goals AS
SELECT
    go.id AS goal_id,
    g.id AS game_id,
    g.name AS game_name,
    COALESCE(g.round_name, g.round) AS round,
    go.team_id,
    t.name AS team_name,
    go.is_own_goal AS own_goal,
    go.phase->>'phase_of_play_label' AS phase_play,
    go.possession_id,
    type_of_play.entity->>'gata_display_name' AS type
FROM goals AS go
JOIN games AS g
    ON g.id = go.game_id
LEFT JOIN teams AS t
    ON t.id = go.team_id
LEFT JOIN type_of_play
    ON type_of_play.id = go.type_of_play_id::text
   AND type_of_play.game_id = go.game_id
"""


def upgrade() -> None:
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_goals")
