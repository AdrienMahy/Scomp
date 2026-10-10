"""Add team-versus-opponent distance deltas.

Revision ID: 20261008_130000
Revises: 20261008_120000
"""

from alembic import op


revision = "20261008_130000"
down_revision = "20261008_120000"
branch_labels = None
depends_on = None


VIEW_SQL = """
CREATE VIEW v_team_distance_opponent_deltas AS
SELECT
    team.game_id,
    team.game_name,
    team.game_date,
    team.game_round,
    team.game_round_name,
    team.season_id,
    team.team_id,
    team.team_name,
    team.team_side,
    opponent.team_id AS opponent_team_id,
    opponent.team_name AS opponent_team_name,
    ROUND(team.total_distance_m - opponent.total_distance_m, 2)
        AS delta_vs_opponent_total_distance_m,
    ROUND(team.mt1_total_distance_m - opponent.mt1_total_distance_m, 2)
        AS delta_vs_opponent_mt1_total_distance_m,
    ROUND(team.mt2_total_distance_m - opponent.mt2_total_distance_m, 2)
        AS delta_vs_opponent_mt2_total_distance_m,
    ROUND(team.walking_m - opponent.walking_m, 2)
        AS delta_vs_opponent_walking_m,
    ROUND(team.jogging_m - opponent.jogging_m, 2)
        AS delta_vs_opponent_jogging_m,
    ROUND(
        team.moderated_intensity_m - opponent.moderated_intensity_m, 2
    ) AS delta_vs_opponent_moderated_intensity_m,
    ROUND(team.high_intensity_m - opponent.high_intensity_m, 2)
        AS delta_vs_opponent_high_intensity_m,
    ROUND(team.sprint_m - opponent.sprint_m, 2)
        AS delta_vs_opponent_sprint_m,
    ROUND(team.mt1_walking_m - opponent.mt1_walking_m, 2)
        AS delta_vs_opponent_mt1_walking_m,
    ROUND(team.mt1_jogging_m - opponent.mt1_jogging_m, 2)
        AS delta_vs_opponent_mt1_jogging_m,
    ROUND(
        team.mt1_moderated_intensity_m
        - opponent.mt1_moderated_intensity_m, 2
    ) AS delta_vs_opponent_mt1_moderated_intensity_m,
    ROUND(team.mt1_high_intensity_m - opponent.mt1_high_intensity_m, 2)
        AS delta_vs_opponent_mt1_high_intensity_m,
    ROUND(team.mt1_sprint_m - opponent.mt1_sprint_m, 2)
        AS delta_vs_opponent_mt1_sprint_m,
    ROUND(team.mt2_walking_m - opponent.mt2_walking_m, 2)
        AS delta_vs_opponent_mt2_walking_m,
    ROUND(team.mt2_jogging_m - opponent.mt2_jogging_m, 2)
        AS delta_vs_opponent_mt2_jogging_m,
    ROUND(
        team.mt2_moderated_intensity_m
        - opponent.mt2_moderated_intensity_m, 2
    ) AS delta_vs_opponent_mt2_moderated_intensity_m,
    ROUND(team.mt2_high_intensity_m - opponent.mt2_high_intensity_m, 2)
        AS delta_vs_opponent_mt2_high_intensity_m,
    ROUND(team.mt2_sprint_m - opponent.mt2_sprint_m, 2)
        AS delta_vs_opponent_mt2_sprint_m,
    ROUND(
        team.high_intensity_distance_m
        - opponent.high_intensity_distance_m, 2
    ) AS delta_vs_opponent_high_intensity_distance_m,
    ROUND(
        team.mt1_high_intensity_m + team.mt1_sprint_m
        - opponent.mt1_high_intensity_m - opponent.mt1_sprint_m, 2
    ) AS delta_vs_opponent_mt1_high_intensity_distance_m,
    ROUND(
        team.mt2_high_intensity_m + team.mt2_sprint_m
        - opponent.mt2_high_intensity_m - opponent.mt2_sprint_m, 2
    ) AS delta_vs_opponent_mt2_high_intensity_distance_m
FROM v_team_distance_absolute AS team
JOIN v_team_distance_absolute AS opponent
    ON opponent.game_id = team.game_id
   AND opponent.team_side = CASE
        WHEN team.team_side = 'HOME' THEN 'AWAY'
        WHEN team.team_side = 'AWAY' THEN 'HOME'
   END
"""


def upgrade() -> None:
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW v_team_distance_opponent_deltas")
