"""Filter the effective playing time view and add competition."""

from alembic import op


revision = "20261107_001000"
down_revision = "20261107_000000"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
DROP VIEW IF EXISTS v_effective_playing_time_by_team;

CREATE VIEW v_effective_playing_time_by_team AS
WITH game_durations AS (
    SELECT
        bip.game_id,
        SUM(NULLIF(bip.entity->>'duration', '')::NUMERIC) AS effective_playing_time
    FROM ball_in_play AS bip
    GROUP BY bip.game_id
)
SELECT
    g.id AS game_id,
    g.name AS game_name,
    COALESCE(g.round_name, g.round) AS round,
    competition.name AS competition_name,
    team.name AS team_name,
    game_durations.effective_playing_time
FROM games AS g
CROSS JOIN LATERAL (
    VALUES (g.home_team_id), (g.away_team_id)
) AS game_teams(team_id)
JOIN teams AS team
    ON team.id = game_teams.team_id
JOIN game_durations
    ON game_durations.game_id = g.id
JOIN competitions AS competition
    ON competition.id = g.competition_id
"""


DOWNGRADE_SQL = """
DROP VIEW IF EXISTS v_effective_playing_time_by_team;

CREATE VIEW v_effective_playing_time_by_team AS
WITH game_durations AS (
    SELECT
        bip.game_id,
        SUM(NULLIF(bip.entity->>'duration', '')::NUMERIC) AS effective_playing_time
    FROM ball_in_play AS bip
    GROUP BY bip.game_id
)
SELECT
    g.id AS game_id,
    g.name AS game_name,
    COALESCE(g.round_name, g.round) AS round,
    team.name AS team_name,
    game_durations.effective_playing_time
FROM games AS g
CROSS JOIN LATERAL (
    VALUES (g.home_team_id), (g.away_team_id)
) AS game_teams(team_id)
JOIN teams AS team
    ON team.id = game_teams.team_id
LEFT JOIN game_durations
    ON game_durations.game_id = g.id
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
