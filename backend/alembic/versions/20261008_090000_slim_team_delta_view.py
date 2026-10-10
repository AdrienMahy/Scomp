"""Keep only team/match identifiers and deltas in the team delta view.

Revision ID: 20261008_090000
Revises: 20261008_080000
"""

from alembic import op


revision = "20261008_090000"
down_revision = "20261008_080000"
branch_labels = None
depends_on = None


IDENTIFIER_COLUMNS = (
    "game_id",
    "game_name",
    "game_date",
    "game_round",
    "game_round_name",
    "team_id",
    "team_name",
    "team_brand",
    "team_side",
    "season_id",
)

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

DELTA_METRICS = (
    "total_distance_m",
    "high_intensity_m",
    "sprint_m",
    "high_intensity_distance_m",
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


def _legacy_reference_column_names() -> tuple[str, ...]:
    return tuple(
        f"season_{stat}_{_metric_suffix(metric)}_m"
        for metric in LEGACY_REFERENCE_METRICS
        for stat in ("max", "avg")
    )


def _delta_column_names() -> tuple[str, ...]:
    metric_deltas = tuple(
        f"delta_{_metric_suffix(metric)}_m" for metric in DELTA_METRICS
    )
    period_deltas = tuple(
        f"delta_period_{suffix}_m"
        for _, _, suffix in PERIOD_DELTA_METRICS
    )
    return metric_deltas + period_deltas


def _match_delta_expressions(
    absolute_alias: str,
    reference_alias: str,
    metrics: tuple[str, ...],
) -> list[str]:
    expressions = []
    for metric in metrics:
        suffix = _metric_suffix(metric)
        expressions.append(
            f"ROUND({absolute_alias}.{metric} "
            f"- {reference_alias}.season_avg_{suffix}_m, 2) "
            f"AS delta_{suffix}_m"
        )
    return expressions


def _period_delta_expressions(alias: str) -> list[str]:
    return [
        f"ROUND({alias}.{mt1_metric} - {alias}.{mt2_metric}, 2) "
        f"AS delta_period_{suffix}_m"
        for mt1_metric, mt2_metric, suffix in PERIOD_DELTA_METRICS
    ]


def _slim_delta_query() -> str:
    expressions = [f"absolute.{column}" for column in IDENTIFIER_COLUMNS]
    expressions.extend(
        _match_delta_expressions(
            "absolute",
            "reference",
            DELTA_METRICS,
        )
    )
    expressions.extend(_period_delta_expressions("absolute"))
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
    expressions = [f"absolute.{column}" for column in BASE_COLUMNS]
    expressions.extend(
        f"reference.{column}"
        for column in _legacy_reference_column_names()
    )
    expressions.extend(
        _match_delta_expressions(
            "absolute",
            "reference",
            LEGACY_REFERENCE_METRICS,
        )
    )
    expressions.extend(_period_delta_expressions("absolute"))
    expressions.extend(f"absolute.{column}" for column in PERIOD_ZONE_COLUMNS)
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_absolute AS absolute
LEFT JOIN v_team_distance_reference AS reference
    ON reference.season_id IS NOT DISTINCT FROM absolute.season_id
   AND reference.team_id IS NOT DISTINCT FROM absolute.team_id
"""


def upgrade() -> None:
    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute(
        "CREATE VIEW v_team_distance_deltas AS " + _slim_delta_query()
    )
    op.execute(
        "CREATE VIEW v_team_distance_summary AS "
        "SELECT * FROM v_team_distance_deltas"
    )


def downgrade() -> None:
    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute(
        "CREATE VIEW v_team_distance_deltas AS " + _legacy_delta_query()
    )
    op.execute(
        "CREATE VIEW v_team_distance_summary AS "
        "SELECT * FROM v_team_distance_deltas"
    )
