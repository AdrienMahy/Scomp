"""Add speed-zone and season metrics to the player distance summary view.

Revision ID: 20261008_010000
Revises: 20261008_000000
"""

from alembic import op


revision = "20261008_010000"
down_revision = "20261008_000000"
branch_labels = None
depends_on = None


PLAYER_DISTANCE_VIEW = """
CREATE OR REPLACE VIEW v_player_distance_summary AS
WITH match_rows AS (
    SELECT
        d.game_id,
        d.player_id,
        d.team_id,
        g.name AS game_name,
        p.name AS player_name,
        t.name AS team_name,
        ROUND((d.match_data->>'total_distance_m')::numeric, 2)
            AS total_distance_m,
        ROUND((d.match_data->>'minutes_played')::numeric, 2)
            AS minutes_played,
        ROUND((d.match_data->>'distance_per_min_played_m')::numeric, 2)
            AS distance_per_min_played_m,
        (d.match_data->'periods'->'MT1'->>'total_distance_m')::numeric
            AS mt1_total_distance_m,
        (d.match_data->'periods'->'MT2'->>'total_distance_m')::numeric
            AS mt2_total_distance_m,
        d.match_data AS full_match_data_jsonb,
        d.intervals AS full_intervals_jsonb,
        g.season_id AS season_id,
        g.round_name AS game_round_name,
        (d.match_data->'speed_zones_m'->>'high_intensity')::numeric
            AS high_intensity_m,
        (d.match_data->'speed_zones_m'->>'sprint')::numeric AS sprint_m,
        (d.match_data->'periods'->'MT1'->'speed_zones_m'
            ->>'high_intensity')::numeric AS mt1_high_intensity_m,
        (d.match_data->'periods'->'MT1'->'speed_zones_m'
            ->>'sprint')::numeric AS mt1_sprint_m,
        (d.match_data->'periods'->'MT2'->'speed_zones_m'
            ->>'high_intensity')::numeric AS mt2_high_intensity_m,
        (d.match_data->'periods'->'MT2'->'speed_zones_m'
            ->>'sprint')::numeric AS mt2_sprint_m
    FROM player_distance_covered d
    LEFT JOIN games g ON d.game_id = g.id
    LEFT JOIN players p ON d.player_id = p.id
    LEFT JOIN teams t ON d.team_id = t.id
)
SELECT
    match_rows.*,
    MAX(total_distance_m) OVER player_season AS season_max_total_distance_m,
    ROUND(AVG(total_distance_m) OVER player_season, 2)
        AS season_avg_total_distance_m,
    MAX(high_intensity_m) OVER player_season AS season_max_high_intensity_m,
    ROUND(AVG(high_intensity_m) OVER player_season, 2)
        AS season_avg_high_intensity_m,
    MAX(sprint_m) OVER player_season AS season_max_sprint_m,
    ROUND(AVG(sprint_m) OVER player_season, 2) AS season_avg_sprint_m,
    MAX(mt1_total_distance_m) OVER player_season
        AS season_max_mt1_total_distance_m,
    ROUND(AVG(mt1_total_distance_m) OVER player_season, 2)
        AS season_avg_mt1_total_distance_m,
    MAX(mt1_high_intensity_m) OVER player_season
        AS season_max_mt1_high_intensity_m,
    ROUND(AVG(mt1_high_intensity_m) OVER player_season, 2)
        AS season_avg_mt1_high_intensity_m,
    MAX(mt1_sprint_m) OVER player_season AS season_max_mt1_sprint_m,
    ROUND(AVG(mt1_sprint_m) OVER player_season, 2)
        AS season_avg_mt1_sprint_m,
    MAX(mt2_total_distance_m) OVER player_season
        AS season_max_mt2_total_distance_m,
    ROUND(AVG(mt2_total_distance_m) OVER player_season, 2)
        AS season_avg_mt2_total_distance_m,
    MAX(mt2_high_intensity_m) OVER player_season
        AS season_max_mt2_high_intensity_m,
    ROUND(AVG(mt2_high_intensity_m) OVER player_season, 2)
        AS season_avg_mt2_high_intensity_m,
    MAX(mt2_sprint_m) OVER player_season AS season_max_mt2_sprint_m,
    ROUND(AVG(mt2_sprint_m) OVER player_season, 2)
        AS season_avg_mt2_sprint_m
FROM match_rows
WINDOW player_season AS (PARTITION BY season_id, player_id)
"""


LEGACY_PLAYER_DISTANCE_VIEW = """
CREATE VIEW v_player_distance_summary AS
SELECT
    d.game_id,
    d.player_id,
    d.team_id,
    g.name AS game_name,
    p.name AS player_name,
    t.name AS team_name,
    ROUND((d.match_data->>'total_distance_m')::numeric, 2)
        AS total_distance_m,
    ROUND((d.match_data->>'minutes_played')::numeric, 2)
        AS minutes_played,
    ROUND((d.match_data->>'distance_per_min_played_m')::numeric, 2)
        AS distance_per_min_played_m,
    (d.match_data->'periods'->'MT1'->>'total_distance_m')::numeric
        AS mt1_total_distance_m,
    (d.match_data->'periods'->'MT2'->>'total_distance_m')::numeric
        AS mt2_total_distance_m,
    d.match_data AS full_match_data_jsonb,
    d.intervals AS full_intervals_jsonb
FROM player_distance_covered d
LEFT JOIN games g ON d.game_id = g.id
LEFT JOIN players p ON d.player_id = p.id
LEFT JOIN teams t ON d.team_id = t.id
"""


def upgrade() -> None:
    op.execute(PLAYER_DISTANCE_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW v_player_distance_summary")
    op.execute(LEGACY_PLAYER_DISTANCE_VIEW)
