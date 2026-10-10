"""Split player distance metrics into absolute, reference, delta, and relative views.

Revision ID: 20261008_050000
Revises: 20261008_040000
"""

from alembic import op


revision = "20261008_050000"
down_revision = "20261008_040000"
branch_labels = None
depends_on = None


ABSOLUTE_QUERY = """
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
"""


def _reference_query(source_view: str) -> str:
    return f"""
SELECT
    absolute.*,
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
FROM {source_view} AS absolute
WINDOW player_season AS (PARTITION BY season_id, player_id)
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


def _relative_query(source_view: str) -> str:
    return f"""
SELECT
    absolute.*,
    ROUND(total_distance_m / NULLIF(minutes_played, 0), 2)
        AS total_distance_per_min_played_m,
    ROUND(high_intensity_m / NULLIF(minutes_played, 0), 2)
        AS high_intensity_per_min_played_m,
    ROUND(sprint_m / NULLIF(minutes_played, 0), 2)
        AS sprint_per_min_played_m
FROM {source_view} AS absolute
"""


def upgrade() -> None:
    op.execute(f"CREATE VIEW v_player_distance_absolute AS {ABSOLUTE_QUERY}")
    op.execute(
        "CREATE VIEW v_player_distance_reference AS "
        + _reference_query("v_player_distance_absolute")
    )
    op.execute(
        "CREATE VIEW v_player_distance_deltas AS "
        + _delta_query("v_player_distance_reference")
    )
    op.execute(
        "CREATE VIEW v_player_distance_relative AS "
        + _relative_query("v_player_distance_absolute")
    )
    op.execute(
        "CREATE OR REPLACE VIEW v_player_distance_summary AS "
        "SELECT * FROM v_player_distance_deltas"
    )


def downgrade() -> None:
    op.execute("DROP VIEW v_player_distance_summary")
    op.execute("DROP VIEW v_player_distance_relative")
    op.execute("DROP VIEW v_player_distance_deltas")
    op.execute("DROP VIEW v_player_distance_reference")
    op.execute("DROP VIEW v_player_distance_absolute")
    op.execute(
        "CREATE VIEW v_player_distance_summary AS "
        "WITH absolute_rows AS ("
        + ABSOLUTE_QUERY
        + "), reference_rows AS ("
        + _reference_query("absolute_rows")
        + ") SELECT * FROM reference_rows"
    )
