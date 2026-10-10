"""Add team deltas for walking, jogging, and moderated intensity.

Revision ID: 20261008_100000
Revises: 20261008_090000
"""

from alembic import op


revision = "20261008_100000"
down_revision = "20261008_090000"
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

EXISTING_DELTA_METRICS = (
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

ADDITIONAL_ZONE_METRICS = (
    "walking_m",
    "jogging_m",
    "moderated_intensity_m",
)


def _metric_suffix(metric: str) -> str:
    return metric[:-2] if metric.endswith("_m") else metric


def _delta_expressions(
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


def _period_delta_expressions(
    alias: str,
    metrics: tuple[str, ...],
) -> list[str]:
    return [
        f"ROUND({alias}.mt1_{_metric_suffix(metric)}_m "
        f"- {alias}.mt2_{_metric_suffix(metric)}_m, 2) "
        f"AS delta_period_{_metric_suffix(metric)}_m"
        for metric in metrics
    ]


def _additional_zone_expressions() -> list[str]:
    expressions = []
    for metric in ADDITIONAL_ZONE_METRICS:
        suffix = _metric_suffix(metric)
        expressions.append(
            f"ROUND(absolute.{metric} "
            f"- reference.season_avg_{suffix}_m, 2) "
            f"AS delta_{suffix}_m"
        )
    for period in ("mt1", "mt2"):
        for metric in ADDITIONAL_ZONE_METRICS:
            suffix = _metric_suffix(metric)
            period_metric = f"{period}_{suffix}_m"
            expressions.append(
                f"ROUND(absolute.{period_metric} "
                f"- reference.season_avg_{period_metric}, 2) "
                f"AS delta_{period_metric}"
            )
    expressions.extend(
        _period_delta_expressions("absolute", ADDITIONAL_ZONE_METRICS)
    )
    return expressions


def _delta_query(include_additional_zones: bool) -> str:
    expressions = [f"absolute.{column}" for column in IDENTIFIER_COLUMNS]
    expressions.extend(
        _delta_expressions(
            "absolute",
            "reference",
            EXISTING_DELTA_METRICS,
        )
    )
    expressions.extend(
        _period_delta_expressions(
            "absolute",
            ("total_distance_m", "high_intensity_m", "sprint_m"),
        )
    )
    if include_additional_zones:
        expressions.extend(_additional_zone_expressions())
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_absolute AS absolute
LEFT JOIN v_team_distance_reference AS reference
    ON reference.season_id IS NOT DISTINCT FROM absolute.season_id
   AND reference.team_id IS NOT DISTINCT FROM absolute.team_id
"""


def _replace_delta_views(include_additional_zones: bool) -> None:
    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute(
        "CREATE VIEW v_team_distance_deltas AS "
        + _delta_query(include_additional_zones)
    )
    op.execute(
        "CREATE VIEW v_team_distance_summary AS "
        "SELECT * FROM v_team_distance_deltas"
    )


def upgrade() -> None:
    _replace_delta_views(include_additional_zones=True)


def downgrade() -> None:
    _replace_delta_views(include_additional_zones=False)
