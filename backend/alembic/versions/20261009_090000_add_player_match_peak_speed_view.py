"""Add maximum run peak speed per player and match.

Revision ID: 20261009_090000
Revises: 20261008_130000
"""

from alembic import op


revision = "20261009_090000"
down_revision = "20261008_130000"
branch_labels = None
depends_on = None


VIEW_SQL = """
CREATE VIEW v_player_match_peak_speed AS
SELECT
    g.id AS game_id,
    g.name AS game_name,
    COALESCE(g.round_name, g.round) AS game_round,
    p.id AS player_id,
    p.name AS player_name,
    MAX(r.peak_speed) AS peak_speed
FROM player_fitness_runs AS r
JOIN games AS g ON g.id = r.game_id
JOIN players AS p ON p.id = r.player_id
GROUP BY
    g.id,
    g.name,
    COALESCE(g.round_name, g.round),
    p.id,
    p.name
"""


def upgrade() -> None:
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW v_player_match_peak_speed")
