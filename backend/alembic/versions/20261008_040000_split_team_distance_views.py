"""Split the team distance summary into absolute, reference, and delta views.

Revision ID: 20261008_040000
Revises: 20261008_030000
"""

from alembic import op


revision = "20261008_040000"
down_revision = "20261008_030000"
branch_labels = None
depends_on = None


ABSOLUTE_QUERY = """
SELECT
    d.game_id,
    g.name AS game_name,
    g.starts_at::date AS game_date,
    g.round AS game_round,
    g.round_name AS game_round_name,
    g.result AS game_result,
    d.team_id,
    t.name AS team_name,
    t.brand AS team_brand,
    CASE
        WHEN d.team_id::text = g.home_team_id::text THEN 'HOME'
        WHEN d.team_id::text = g.away_team_id::text THEN 'AWAY'
        ELSE 'UNKNOWN'
    END AS team_side,
    (d.match_data->>'total_distance_m')::numeric AS total_distance_m,
    (d.match_data->>'minutes_played')::numeric AS minutes_played,
    (d.match_data->'speed_zones_m'->>'walking')::numeric AS walking_m,
    (d.match_data->'speed_zones_m'->>'jogging')::numeric AS jogging_m,
    (d.match_data->'speed_zones_m'->>'moderated_intensity')::numeric
        AS moderated_intensity_m,
    (d.match_data->'speed_zones_m'->>'high_intensity')::numeric
        AS high_intensity_m,
    (d.match_data->'speed_zones_m'->>'sprint')::numeric AS sprint_m,
    (
        (d.match_data->'speed_zones_m'->>'high_intensity')::numeric
        + (d.match_data->'speed_zones_m'->>'sprint')::numeric
    ) AS high_intensity_distance_m,
    (
        (d.match_data->'speed_zones_m'->>'walking')::numeric
        + (d.match_data->'speed_zones_m'->>'jogging')::numeric
    ) AS low_intensity_distance_m,
    CASE
        WHEN (d.match_data->>'total_distance_m')::numeric > 0
        THEN ROUND((
            (
                (d.match_data->'speed_zones_m'->>'high_intensity')::numeric
                + (d.match_data->'speed_zones_m'->>'sprint')::numeric
            ) / (d.match_data->>'total_distance_m')::numeric * 100
        ), 2)
        ELSE NULL
    END AS high_intensity_ratio_percent,
    ROUND(((d.match_data->>'total_distance_m')::numeric / 90), 2)
        AS avg_speed_m_per_minute,
    d.created_at,
    d.updated_at,
    jsonb_build_object(
        'total_distance_m', d.match_data->'total_distance_m',
        'minutes_played', d.match_data->'minutes_played'
    ) AS full_metrics_jsonb,
    d.match_data->'speed_zones_m' AS full_speed_zones_jsonb,
    d.match_data->'game_state_m' AS full_game_state_jsonb,
    d.intervals AS full_time_intervals_jsonb,
    d.match_data AS full_match_data_jsonb,
    d.intervals AS full_intervals_jsonb,
    g.season_id,
    (d.match_data->'periods'->'MT1'->>'total_distance_m')::numeric
        AS mt1_total_distance_m,
    (d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'high_intensity')::numeric AS mt1_high_intensity_m,
    (d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'sprint')::numeric AS mt1_sprint_m,
    (d.match_data->'periods'->'MT2'->>'total_distance_m')::numeric
        AS mt2_total_distance_m,
    (d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'high_intensity')::numeric AS mt2_high_intensity_m,
    (d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'sprint')::numeric AS mt2_sprint_m
FROM team_distance_covered d
LEFT JOIN games g ON d.game_id::text = g.id::text
LEFT JOIN teams t ON d.team_id::text = t.id::text
"""


def _reference_query(source_view: str) -> str:
    return f"""
SELECT
    absolute.*,
    MAX(total_distance_m) OVER team_season AS season_max_total_distance_m,
    ROUND(AVG(total_distance_m) OVER team_season, 2)
        AS season_avg_total_distance_m,
    MAX(high_intensity_m) OVER team_season AS season_max_high_intensity_m,
    ROUND(AVG(high_intensity_m) OVER team_season, 2)
        AS season_avg_high_intensity_m,
    MAX(sprint_m) OVER team_season AS season_max_sprint_m,
    ROUND(AVG(sprint_m) OVER team_season, 2) AS season_avg_sprint_m,
    MAX(mt1_total_distance_m) OVER team_season
        AS season_max_mt1_total_distance_m,
    ROUND(AVG(mt1_total_distance_m) OVER team_season, 2)
        AS season_avg_mt1_total_distance_m,
    MAX(mt1_high_intensity_m) OVER team_season
        AS season_max_mt1_high_intensity_m,
    ROUND(AVG(mt1_high_intensity_m) OVER team_season, 2)
        AS season_avg_mt1_high_intensity_m,
    MAX(mt1_sprint_m) OVER team_season AS season_max_mt1_sprint_m,
    ROUND(AVG(mt1_sprint_m) OVER team_season, 2)
        AS season_avg_mt1_sprint_m,
    MAX(mt2_total_distance_m) OVER team_season
        AS season_max_mt2_total_distance_m,
    ROUND(AVG(mt2_total_distance_m) OVER team_season, 2)
        AS season_avg_mt2_total_distance_m,
    MAX(mt2_high_intensity_m) OVER team_season
        AS season_max_mt2_high_intensity_m,
    ROUND(AVG(mt2_high_intensity_m) OVER team_season, 2)
        AS season_avg_mt2_high_intensity_m,
    MAX(mt2_sprint_m) OVER team_season AS season_max_mt2_sprint_m,
    ROUND(AVG(mt2_sprint_m) OVER team_season, 2)
        AS season_avg_mt2_sprint_m
FROM {source_view} AS absolute
WINDOW team_season AS (PARTITION BY season_id, team_id)
"""


def _delta_query(source_view: str) -> str:
    return f"""
SELECT
    reference.*,
    ROUND(total_distance_m - season_avg_total_distance_m, 2)
        AS delta_total_distance_m,
    ROUND(high_intensity_m - season_avg_high_intensity_m, 2)
        AS delta_high_intensity_m,
    ROUND(sprint_m - season_avg_sprint_m, 2) AS delta_sprint_m,
    ROUND(mt1_total_distance_m - season_avg_mt1_total_distance_m, 2)
        AS delta_mt1_total_distance_m,
    ROUND(mt1_high_intensity_m - season_avg_mt1_high_intensity_m, 2)
        AS delta_mt1_high_intensity_m,
    ROUND(mt1_sprint_m - season_avg_mt1_sprint_m, 2)
        AS delta_mt1_sprint_m,
    ROUND(mt2_total_distance_m - season_avg_mt2_total_distance_m, 2)
        AS delta_mt2_total_distance_m,
    ROUND(mt2_high_intensity_m - season_avg_mt2_high_intensity_m, 2)
        AS delta_mt2_high_intensity_m,
    ROUND(mt2_sprint_m - season_avg_mt2_sprint_m, 2)
        AS delta_mt2_sprint_m,
    ROUND(mt1_total_distance_m - mt2_total_distance_m, 2)
        AS delta_period_total_distance_m,
    ROUND(mt1_high_intensity_m - mt2_high_intensity_m, 2)
        AS delta_period_high_intensity_m,
    ROUND(mt1_sprint_m - mt2_sprint_m, 2)
        AS delta_period_sprint_m
FROM {source_view} AS reference
"""


def upgrade() -> None:
    op.execute(f"CREATE VIEW v_team_distance_absolute AS {ABSOLUTE_QUERY}")
    op.execute(
        "CREATE VIEW v_team_distance_reference AS "
        + _reference_query("v_team_distance_absolute")
    )
    op.execute(
        "CREATE VIEW v_team_distance_deltas AS "
        + _delta_query("v_team_distance_reference")
    )
    op.execute(
        "CREATE OR REPLACE VIEW v_team_distance_summary AS "
        "SELECT * FROM v_team_distance_deltas"
    )


def downgrade() -> None:
    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute("DROP VIEW v_team_distance_reference")
    op.execute("DROP VIEW v_team_distance_absolute")

    op.execute(
        "CREATE VIEW v_team_distance_summary AS "
        "WITH absolute_rows AS ("
        + ABSOLUTE_QUERY
        + "), reference_rows AS ("
        + _reference_query("absolute_rows")
        + "), delta_rows AS ("
        + _delta_query("reference_rows")
        + ") SELECT * FROM delta_rows"
    )
