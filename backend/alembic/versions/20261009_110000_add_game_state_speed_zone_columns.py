"""Add speed-zone distances to game-state views.

Revision ID: 20261009_110000
Revises: 20261009_100000
"""

from alembic import op


revision = "20261009_110000"
down_revision = "20261009_100000"
branch_labels = None
depends_on = None


TEAM_VIEW_SQL = """
CREATE OR REPLACE VIEW v_team_distance_game_state AS
SELECT
    g.id AS game_id,
    g.name AS game_name,
    g.starts_at::date AS game_date,
    COALESCE(g.round_name, g.round) AS game_round,
    d.team_id,
    t.name AS team_name,
    CASE
        WHEN d.team_id = g.home_team_id THEN 'HOME'
        WHEN d.team_id = g.away_team_id THEN 'AWAY'
        ELSE 'UNKNOWN'
    END AS team_side,
    (d.match_data->'game_state_m'->>'in_play')::numeric
        AS in_play_distance_m,
    (d.match_data->'game_state_m'->>'out_of_play')::numeric
        AS out_of_play_distance_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'walking')::numeric AS in_play_walking_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'jogging')::numeric AS in_play_jogging_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'moderated_intensity')::numeric AS in_play_moderated_intensity_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'high_intensity')::numeric AS in_play_high_intensity_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'sprint')::numeric AS in_play_sprint_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'walking')::numeric AS out_of_play_walking_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'jogging')::numeric AS out_of_play_jogging_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'moderated_intensity')::numeric AS out_of_play_moderated_intensity_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'high_intensity')::numeric AS out_of_play_high_intensity_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'sprint')::numeric AS out_of_play_sprint_m
FROM team_distance_covered AS d
JOIN games AS g ON g.id = d.game_id
LEFT JOIN teams AS t ON t.id = d.team_id
"""


PLAYER_VIEW_SQL = """
CREATE OR REPLACE VIEW v_player_distance_game_state AS
SELECT
    g.id AS game_id,
    g.name AS game_name,
    g.starts_at::date AS game_date,
    COALESCE(g.round_name, g.round) AS game_round,
    d.player_id,
    p.name AS player_name,
    d.team_id,
    t.name AS team_name,
    CASE
        WHEN d.team_id = g.home_team_id THEN 'HOME'
        WHEN d.team_id = g.away_team_id THEN 'AWAY'
        ELSE 'UNKNOWN'
    END AS team_side,
    (d.match_data->'game_state_m'->>'in_play')::numeric
        AS in_play_distance_m,
    (d.match_data->'game_state_m'->>'out_of_play')::numeric
        AS out_of_play_distance_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'walking')::numeric AS in_play_walking_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'jogging')::numeric AS in_play_jogging_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'moderated_intensity')::numeric AS in_play_moderated_intensity_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'high_intensity')::numeric AS in_play_high_intensity_m,
    (d.match_data->'game_state_by_speed_zone_m'->'in_play'
        ->>'sprint')::numeric AS in_play_sprint_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'walking')::numeric AS out_of_play_walking_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'jogging')::numeric AS out_of_play_jogging_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'moderated_intensity')::numeric AS out_of_play_moderated_intensity_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'high_intensity')::numeric AS out_of_play_high_intensity_m,
    (d.match_data->'game_state_by_speed_zone_m'->'out_of_play'
        ->>'sprint')::numeric AS out_of_play_sprint_m
FROM player_distance_covered AS d
JOIN games AS g ON g.id = d.game_id
LEFT JOIN players AS p ON p.id = d.player_id
LEFT JOIN teams AS t ON t.id = d.team_id
"""


def upgrade() -> None:
    op.execute(TEAM_VIEW_SQL)
    op.execute(PLAYER_VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW v_player_distance_game_state")
    op.execute("DROP VIEW v_team_distance_game_state")
    op.execute(
        """
        CREATE OR REPLACE VIEW v_team_distance_game_state AS
        SELECT
            g.id AS game_id,
            g.name AS game_name,
            g.starts_at::date AS game_date,
            COALESCE(g.round_name, g.round) AS game_round,
            d.team_id,
            t.name AS team_name,
            CASE
                WHEN d.team_id = g.home_team_id THEN 'HOME'
                WHEN d.team_id = g.away_team_id THEN 'AWAY'
                ELSE 'UNKNOWN'
            END AS team_side,
            (d.match_data->'game_state_m'->>'in_play')::numeric
                AS in_play_distance_m,
            (d.match_data->'game_state_m'->>'out_of_play')::numeric
                AS out_of_play_distance_m
        FROM team_distance_covered AS d
        JOIN games AS g ON g.id = d.game_id
        LEFT JOIN teams AS t ON t.id = d.team_id
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_player_distance_game_state AS
        SELECT
            g.id AS game_id,
            g.name AS game_name,
            g.starts_at::date AS game_date,
            COALESCE(g.round_name, g.round) AS game_round,
            d.player_id,
            p.name AS player_name,
            d.team_id,
            t.name AS team_name,
            CASE
                WHEN d.team_id = g.home_team_id THEN 'HOME'
                WHEN d.team_id = g.away_team_id THEN 'AWAY'
                ELSE 'UNKNOWN'
            END AS team_side,
            (d.match_data->'game_state_m'->>'in_play')::numeric
                AS in_play_distance_m,
            (d.match_data->'game_state_m'->>'out_of_play')::numeric
                AS out_of_play_distance_m
        FROM player_distance_covered AS d
        JOIN games AS g ON g.id = d.game_id
        LEFT JOIN players AS p ON p.id = d.player_id
        LEFT JOIN teams AS t ON t.id = d.team_id
        """
    )
