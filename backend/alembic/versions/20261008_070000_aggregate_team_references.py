"""Aggregate team reference statistics by team and season.

Revision ID: 20261008_070000
Revises: 20261008_060000
"""

from alembic import op


revision = "20261008_070000"
down_revision = "20261008_060000"
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

PERIOD_ZONE_COLUMNS = (
    "mt1_walking_m",
    "mt1_jogging_m",
    "mt1_moderated_intensity_m",
    "mt2_walking_m",
    "mt2_jogging_m",
    "mt2_moderated_intensity_m",
)

REFERENCE_METRICS = (
    "total_distance_m",
    "walking_m",
    "jogging_m",
    "moderated_intensity_m",
    "high_intensity_m",
    "sprint_m",
    "mt1_total_distance_m",
    "mt1_walking_m",
    "mt1_jogging_m",
    "mt1_moderated_intensity_m",
    "mt1_high_intensity_m",
    "mt1_sprint_m",
    "mt2_total_distance_m",
    "mt2_walking_m",
    "mt2_jogging_m",
    "mt2_moderated_intensity_m",
    "mt2_high_intensity_m",
    "mt2_sprint_m",
)

DELTA_METRICS = (
    "total_distance_m",
    "high_intensity_m",
    "sprint_m",
    "mt1_total_distance_m",
    "mt1_high_intensity_m",
    "mt1_sprint_m",
    "mt2_total_distance_m",
    "mt2_high_intensity_m",
    "mt2_sprint_m",
)

PERIOD_DELTA_METRICS = (
    ("mt1_total_distance_m", "mt2_total_distance_m", "total_distance"),
    ("mt1_high_intensity_m", "mt2_high_intensity_m", "high_intensity"),
    ("mt1_sprint_m", "mt2_sprint_m", "sprint"),
)


def _metric_suffix(metric: str) -> str:
    return metric[:-2] if metric.endswith("_m") else metric


def _reference_column_names(metrics: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        f"season_{stat}_{_metric_suffix(metric)}_m"
        for metric in metrics
        for stat in ("max", "avg")
    )


LEGACY_REFERENCE_METRICS = (
    "total_distance_m",
    "high_intensity_m",
    "sprint_m",
    "mt1_total_distance_m",
    "mt1_high_intensity_m",
    "mt1_sprint_m",
    "mt2_total_distance_m",
    "mt2_high_intensity_m",
    "mt2_sprint_m",
)

LEGACY_REFERENCE_COLUMNS = _reference_column_names(LEGACY_REFERENCE_METRICS)
REFERENCE_COLUMNS = _reference_column_names(REFERENCE_METRICS)
DELTA_COLUMNS = tuple(
    f"delta_{_metric_suffix(metric)}_m" for metric in DELTA_METRICS
) + tuple(
    f"delta_period_{metric}_m"
    for _, _, metric in PERIOD_DELTA_METRICS
)


def _column_list(alias: str, columns: tuple[str, ...]) -> list[str]:
    return [f"{alias}.{column}" for column in columns]


def _reference_expressions(
    alias: str,
    metrics: tuple[str, ...],
    grouped: bool,
) -> list[str]:
    expressions = []
    for metric in metrics:
        suffix = _metric_suffix(metric)
        if grouped:
            expressions.extend(
                (
                    f"MAX({alias}.{metric}) AS season_max_{suffix}_m",
                    f"ROUND(AVG({alias}.{metric}), 2) "
                    f"AS season_avg_{suffix}_m",
                )
            )
        else:
            expressions.extend(
                (
                    f"MAX({alias}.{metric}) OVER team_season "
                    f"AS season_max_{suffix}_m",
                    f"ROUND(AVG({alias}.{metric}) OVER team_season, 2) "
                    f"AS season_avg_{suffix}_m",
                )
            )
    return expressions


def _grouped_reference_query() -> str:
    expressions = [
        "absolute.season_id",
        "absolute.team_id",
        "MAX(absolute.team_name) AS team_name",
        "MAX(absolute.team_brand) AS team_brand",
    ]
    expressions.extend(
        _reference_expressions("absolute", REFERENCE_METRICS, grouped=True)
    )
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_absolute AS absolute
GROUP BY absolute.season_id, absolute.team_id
"""


def _legacy_reference_query() -> str:
    expressions = _column_list("absolute", BASE_COLUMNS)
    expressions.extend(
        _reference_expressions(
            "absolute", LEGACY_REFERENCE_METRICS, grouped=False
        )
    )
    expressions.extend(_column_list("absolute", PERIOD_ZONE_COLUMNS))
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_absolute AS absolute
WINDOW team_season AS (
    PARTITION BY absolute.season_id, absolute.team_id
)
"""


def _delta_expressions(absolute_alias: str, reference_alias: str) -> list[str]:
    expressions = []
    for metric in DELTA_METRICS:
        suffix = _metric_suffix(metric)
        expressions.append(
            f"ROUND({absolute_alias}.{metric} "
            f"- {reference_alias}.season_avg_{suffix}_m, 2) "
            f"AS delta_{suffix}_m"
        )
    for mt1_metric, mt2_metric, suffix in PERIOD_DELTA_METRICS:
        expressions.append(
            f"ROUND({absolute_alias}.{mt1_metric} "
            f"- {absolute_alias}.{mt2_metric}, 2) "
            f"AS delta_period_{suffix}_m"
        )
    return expressions


def _grouped_delta_query() -> str:
    expressions = _column_list("absolute", BASE_COLUMNS)
    expressions.extend(_column_list("reference", LEGACY_REFERENCE_COLUMNS))
    expressions.extend(_delta_expressions("absolute", "reference"))
    expressions.extend(_column_list("absolute", PERIOD_ZONE_COLUMNS))
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_absolute AS absolute
LEFT JOIN v_team_distance_reference AS reference
    ON reference.season_id IS NOT DISTINCT FROM absolute.season_id
   AND reference.team_id IS NOT DISTINCT FROM absolute.team_id
"""


def _legacy_delta_query() -> str:
    expressions = _column_list("reference", BASE_COLUMNS)
    expressions.extend(_column_list("reference", LEGACY_REFERENCE_COLUMNS))
    expressions.extend(_delta_expressions("reference", "reference"))
    expressions.extend(_column_list("reference", PERIOD_ZONE_COLUMNS))
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_reference AS reference
"""


def _create_legacy_views() -> None:
    op.execute(
        "CREATE VIEW v_team_distance_reference AS "
        + _legacy_reference_query()
    )
    op.execute(
        "CREATE VIEW v_team_distance_deltas AS "
        + _legacy_delta_query()
    )
    op.execute(
        "CREATE VIEW v_team_distance_summary AS "
        "SELECT * FROM v_team_distance_deltas"
    )


def upgrade() -> None:
    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute("DROP VIEW v_team_distance_reference")
    op.execute(
        "CREATE VIEW v_team_distance_reference AS "
        + _grouped_reference_query()
    )
    op.execute(
        "CREATE VIEW v_team_distance_deltas AS "
        + _grouped_delta_query()
    )
    op.execute(
        "CREATE VIEW v_team_distance_summary AS "
        "SELECT * FROM v_team_distance_deltas"
    )


def downgrade() -> None:
    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute("DROP VIEW v_team_distance_reference")
    _create_legacy_views()
