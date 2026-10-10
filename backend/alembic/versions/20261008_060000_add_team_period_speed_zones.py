"""Expose all speed zones for each team match period.

Revision ID: 20261008_060000
Revises: 20261008_050000
"""

from alembic import op


revision = "20261008_060000"
down_revision = "20261008_050000"
branch_labels = None
depends_on = None


BASE_COLUMNS = (
    "game_id",
    "game_name",
    "game_date",
    "game_round",
    "game_round_name",
    "game_result",
    "team_id",
    "team_name",
    "team_brand",
    "team_side",
    "total_distance_m",
    "minutes_played",
    "walking_m",
    "jogging_m",
    "moderated_intensity_m",
    "high_intensity_m",
    "sprint_m",
    "high_intensity_distance_m",
    "low_intensity_distance_m",
    "high_intensity_ratio_percent",
    "avg_speed_m_per_minute",
    "created_at",
    "updated_at",
    "full_metrics_jsonb",
    "full_speed_zones_jsonb",
    "full_game_state_jsonb",
    "full_time_intervals_jsonb",
    "full_match_data_jsonb",
    "full_intervals_jsonb",
    "season_id",
    "mt1_total_distance_m",
    "mt1_high_intensity_m",
    "mt1_sprint_m",
    "mt2_total_distance_m",
    "mt2_high_intensity_m",
    "mt2_sprint_m",
)

REFERENCE_COLUMNS = (
    "season_max_total_distance_m",
    "season_avg_total_distance_m",
    "season_max_high_intensity_m",
    "season_avg_high_intensity_m",
    "season_max_sprint_m",
    "season_avg_sprint_m",
    "season_max_mt1_total_distance_m",
    "season_avg_mt1_total_distance_m",
    "season_max_mt1_high_intensity_m",
    "season_avg_mt1_high_intensity_m",
    "season_max_mt1_sprint_m",
    "season_avg_mt1_sprint_m",
    "season_max_mt2_total_distance_m",
    "season_avg_mt2_total_distance_m",
    "season_max_mt2_high_intensity_m",
    "season_avg_mt2_high_intensity_m",
    "season_max_mt2_sprint_m",
    "season_avg_mt2_sprint_m",
)

DELTA_COLUMNS = (
    "delta_total_distance_m",
    "delta_high_intensity_m",
    "delta_sprint_m",
    "delta_mt1_total_distance_m",
    "delta_mt1_high_intensity_m",
    "delta_mt1_sprint_m",
    "delta_mt2_total_distance_m",
    "delta_mt2_high_intensity_m",
    "delta_mt2_sprint_m",
    "delta_period_total_distance_m",
    "delta_period_high_intensity_m",
    "delta_period_sprint_m",
)

PERIOD_ZONE_COLUMNS = (
    "mt1_walking_m",
    "mt1_jogging_m",
    "mt1_moderated_intensity_m",
    "mt2_walking_m",
    "mt2_jogging_m",
    "mt2_moderated_intensity_m",
)

ABSOLUTE_EXPRESSIONS = (
    "d.game_id",
    "g.name AS game_name",
    "g.starts_at::date AS game_date",
    "g.round AS game_round",
    "g.round_name AS game_round_name",
    "g.result AS game_result",
    "d.team_id",
    "t.name AS team_name",
    "t.brand AS team_brand",
    """CASE
        WHEN d.team_id::text = g.home_team_id::text THEN 'HOME'
        WHEN d.team_id::text = g.away_team_id::text THEN 'AWAY'
        ELSE 'UNKNOWN'
    END AS team_side""",
    "(d.match_data->>'total_distance_m')::numeric AS total_distance_m",
    "(d.match_data->>'minutes_played')::numeric AS minutes_played",
    "(d.match_data->'speed_zones_m'->>'walking')::numeric AS walking_m",
    "(d.match_data->'speed_zones_m'->>'jogging')::numeric AS jogging_m",
    """(d.match_data->'speed_zones_m'->>'moderated_intensity')::numeric
        AS moderated_intensity_m""",
    "(d.match_data->'speed_zones_m'->>'high_intensity')::numeric "
    "AS high_intensity_m",
    "(d.match_data->'speed_zones_m'->>'sprint')::numeric AS sprint_m",
    """(
        (d.match_data->'speed_zones_m'->>'high_intensity')::numeric
        + (d.match_data->'speed_zones_m'->>'sprint')::numeric
    ) AS high_intensity_distance_m""",
    """(
        (d.match_data->'speed_zones_m'->>'walking')::numeric
        + (d.match_data->'speed_zones_m'->>'jogging')::numeric
    ) AS low_intensity_distance_m""",
    """CASE
        WHEN (d.match_data->>'total_distance_m')::numeric > 0
        THEN ROUND((
            (
                (d.match_data->'speed_zones_m'->>'high_intensity')::numeric
                + (d.match_data->'speed_zones_m'->>'sprint')::numeric
            ) / (d.match_data->>'total_distance_m')::numeric * 100
        ), 2)
        ELSE NULL
    END AS high_intensity_ratio_percent""",
    """ROUND(((d.match_data->>'total_distance_m')::numeric / 90), 2)
        AS avg_speed_m_per_minute""",
    "d.created_at",
    "d.updated_at",
    """jsonb_build_object(
        'total_distance_m', d.match_data->'total_distance_m',
        'minutes_played', d.match_data->'minutes_played'
    ) AS full_metrics_jsonb""",
    "d.match_data->'speed_zones_m' AS full_speed_zones_jsonb",
    "d.match_data->'game_state_m' AS full_game_state_jsonb",
    "d.intervals AS full_time_intervals_jsonb",
    "d.match_data AS full_match_data_jsonb",
    "d.intervals AS full_intervals_jsonb",
    "g.season_id",
    """(d.match_data->'periods'->'MT1'->>'total_distance_m')::numeric
        AS mt1_total_distance_m""",
    """(d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'high_intensity')::numeric AS mt1_high_intensity_m""",
    """(d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'sprint')::numeric AS mt1_sprint_m""",
    """(d.match_data->'periods'->'MT2'->>'total_distance_m')::numeric
        AS mt2_total_distance_m""",
    """(d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'high_intensity')::numeric AS mt2_high_intensity_m""",
    """(d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'sprint')::numeric AS mt2_sprint_m""",
)

PERIOD_ZONE_EXPRESSIONS = (
    """(d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'walking')::numeric AS mt1_walking_m""",
    """(d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'jogging')::numeric AS mt1_jogging_m""",
    """(d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'moderated_intensity')::numeric AS mt1_moderated_intensity_m""",
    """(d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'walking')::numeric AS mt2_walking_m""",
    """(d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'jogging')::numeric AS mt2_jogging_m""",
    """(d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'moderated_intensity')::numeric AS mt2_moderated_intensity_m""",
)

REFERENCE_EXPRESSIONS = (
    "MAX(absolute.total_distance_m) OVER team_season "
    "AS season_max_total_distance_m",
    "ROUND(AVG(absolute.total_distance_m) OVER team_season, 2) "
    "AS season_avg_total_distance_m",
    "MAX(absolute.high_intensity_m) OVER team_season "
    "AS season_max_high_intensity_m",
    "ROUND(AVG(absolute.high_intensity_m) OVER team_season, 2) "
    "AS season_avg_high_intensity_m",
    "MAX(absolute.sprint_m) OVER team_season AS season_max_sprint_m",
    "ROUND(AVG(absolute.sprint_m) OVER team_season, 2) "
    "AS season_avg_sprint_m",
    "MAX(absolute.mt1_total_distance_m) OVER team_season "
    "AS season_max_mt1_total_distance_m",
    "ROUND(AVG(absolute.mt1_total_distance_m) OVER team_season, 2) "
    "AS season_avg_mt1_total_distance_m",
    "MAX(absolute.mt1_high_intensity_m) OVER team_season "
    "AS season_max_mt1_high_intensity_m",
    "ROUND(AVG(absolute.mt1_high_intensity_m) OVER team_season, 2) "
    "AS season_avg_mt1_high_intensity_m",
    "MAX(absolute.mt1_sprint_m) OVER team_season "
    "AS season_max_mt1_sprint_m",
    "ROUND(AVG(absolute.mt1_sprint_m) OVER team_season, 2) "
    "AS season_avg_mt1_sprint_m",
    "MAX(absolute.mt2_total_distance_m) OVER team_season "
    "AS season_max_mt2_total_distance_m",
    "ROUND(AVG(absolute.mt2_total_distance_m) OVER team_season, 2) "
    "AS season_avg_mt2_total_distance_m",
    "MAX(absolute.mt2_high_intensity_m) OVER team_season "
    "AS season_max_mt2_high_intensity_m",
    "ROUND(AVG(absolute.mt2_high_intensity_m) OVER team_season, 2) "
    "AS season_avg_mt2_high_intensity_m",
    "MAX(absolute.mt2_sprint_m) OVER team_season "
    "AS season_max_mt2_sprint_m",
    "ROUND(AVG(absolute.mt2_sprint_m) OVER team_season, 2) "
    "AS season_avg_mt2_sprint_m",
)

DELTA_EXPRESSIONS = (
    "ROUND(reference.total_distance_m - reference.season_avg_total_distance_m, 2) "
    "AS delta_total_distance_m",
    "ROUND(reference.high_intensity_m - reference.season_avg_high_intensity_m, 2) "
    "AS delta_high_intensity_m",
    "ROUND(reference.sprint_m - reference.season_avg_sprint_m, 2) "
    "AS delta_sprint_m",
    """ROUND(
        reference.mt1_total_distance_m - reference.season_avg_mt1_total_distance_m,
        2
    ) AS delta_mt1_total_distance_m""",
    """ROUND(
        reference.mt1_high_intensity_m
        - reference.season_avg_mt1_high_intensity_m,
        2
    ) AS delta_mt1_high_intensity_m""",
    """ROUND(
        reference.mt1_sprint_m - reference.season_avg_mt1_sprint_m,
        2
    ) AS delta_mt1_sprint_m""",
    """ROUND(
        reference.mt2_total_distance_m - reference.season_avg_mt2_total_distance_m,
        2
    ) AS delta_mt2_total_distance_m""",
    """ROUND(
        reference.mt2_high_intensity_m
        - reference.season_avg_mt2_high_intensity_m,
        2
    ) AS delta_mt2_high_intensity_m""",
    """ROUND(
        reference.mt2_sprint_m - reference.season_avg_mt2_sprint_m,
        2
    ) AS delta_mt2_sprint_m""",
    """ROUND(
        reference.mt1_total_distance_m - reference.mt2_total_distance_m,
        2
    ) AS delta_period_total_distance_m""",
    """ROUND(
        reference.mt1_high_intensity_m - reference.mt2_high_intensity_m,
        2
    ) AS delta_period_high_intensity_m""",
    """ROUND(
        reference.mt1_sprint_m - reference.mt2_sprint_m,
        2
    ) AS delta_period_sprint_m""",
)


def _absolute_query(include_period_zones: bool) -> str:
    expressions = list(ABSOLUTE_EXPRESSIONS)
    if include_period_zones:
        expressions.extend(PERIOD_ZONE_EXPRESSIONS)
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM team_distance_covered d
LEFT JOIN games g ON d.game_id::text = g.id::text
LEFT JOIN teams t ON d.team_id::text = t.id::text
"""


def _reference_query(include_period_zones: bool) -> str:
    expressions = [f"absolute.{column}" for column in BASE_COLUMNS]
    expressions.extend(REFERENCE_EXPRESSIONS)
    if include_period_zones:
        expressions.extend(
            f"absolute.{column}" for column in PERIOD_ZONE_COLUMNS
        )
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_absolute AS absolute
WINDOW team_season AS (
    PARTITION BY absolute.season_id, absolute.team_id
)
"""


def _delta_query(include_period_zones: bool) -> str:
    reference_columns = BASE_COLUMNS + REFERENCE_COLUMNS
    expressions = [f"reference.{column}" for column in reference_columns]
    expressions.extend(DELTA_EXPRESSIONS)
    if include_period_zones:
        expressions.extend(
            f"reference.{column}" for column in PERIOD_ZONE_COLUMNS
        )
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_reference AS reference
"""


def _create_team_views(include_period_zones: bool) -> None:
    create_statement = "CREATE OR REPLACE VIEW" if include_period_zones else "CREATE VIEW"
    op.execute(
        f"{create_statement} v_team_distance_absolute AS "
        + _absolute_query(include_period_zones)
    )
    op.execute(
        f"{create_statement} v_team_distance_reference AS "
        + _reference_query(include_period_zones)
    )
    op.execute(
        f"{create_statement} v_team_distance_deltas AS "
        + _delta_query(include_period_zones)
    )
    op.execute(
        f"{create_statement} v_team_distance_summary AS "
        "SELECT * FROM v_team_distance_deltas"
    )


def upgrade() -> None:
    _create_team_views(include_period_zones=True)


def downgrade() -> None:
    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute("DROP VIEW v_team_distance_reference")
    op.execute("DROP VIEW v_team_distance_absolute")
    _create_team_views(include_period_zones=False)
