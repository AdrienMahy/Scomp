"""Add MT1-versus-MT2 high-intensity-plus-sprint deltas.

Revision ID: 20261009_130000
Revises: 20261009_120000
"""

from alembic import op


revision = "20261009_130000"
down_revision = "20261009_120000"
branch_labels = None
depends_on = None


TEAM_IDENTIFIERS = (
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

TEAM_REFERENCE_METRICS = (
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

TEAM_CORE_PERIOD_METRICS = (
    "total_distance_m",
    "high_intensity_m",
    "sprint_m",
)

TEAM_ADDITIONAL_ZONE_METRICS = (
    "walking_m",
    "jogging_m",
    "moderated_intensity_m",
)

PLAYER_IDENTIFIERS = (
    "game_id",
    "game_name",
    "game_round_name",
    "player_id",
    "player_name",
    "team_id",
    "team_name",
    "season_id",
)

PLAYER_DELTA_METRICS = (
    "total_distance_m",
    "walking_m",
    "jogging_m",
    "moderated_intensity_m",
    "high_intensity_m",
    "sprint_m",
    "high_intensity_distance_m",
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

PLAYER_PERIOD_METRICS = (
    "total_distance_m",
    "walking_m",
    "jogging_m",
    "moderated_intensity_m",
    "high_intensity_m",
    "sprint_m",
)


def _metric_suffix(metric: str) -> str:
    return metric[:-2] if metric.endswith("_m") else metric


def _reference_delta(metric: str) -> str:
    suffix = _metric_suffix(metric)
    return (
        f"ROUND(absolute.{metric} "
        f"- reference.season_avg_{suffix}_m, 2) "
        f"AS delta_{suffix}_m"
    )


def _period_delta(metric: str) -> str:
    suffix = _metric_suffix(metric)
    return (
        f"ROUND(absolute.mt1_{suffix}_m "
        f"- absolute.mt2_{suffix}_m, 2) "
        f"AS delta_period_{suffix}_m"
    )


def _derived_period_delta() -> str:
    return """
ROUND(
    (absolute.mt1_high_intensity_m + absolute.mt1_sprint_m)
    - (absolute.mt2_high_intensity_m + absolute.mt2_sprint_m),
    2
) AS delta_period_high_intensity_distance_m
"""


def _additional_team_deltas() -> list[str]:
    expressions = [
        _reference_delta(metric)
        for metric in TEAM_ADDITIONAL_ZONE_METRICS
    ]
    for period in ("mt1", "mt2"):
        expressions.extend(
            _reference_delta(f"{period}_{metric}")
            for metric in TEAM_ADDITIONAL_ZONE_METRICS
        )
    expressions.extend(
        _period_delta(metric)
        for metric in TEAM_ADDITIONAL_ZONE_METRICS
    )
    return expressions


def _team_delta_query(include_period_combined: bool) -> str:
    expressions = [f"absolute.{column}" for column in TEAM_IDENTIFIERS]
    expressions.extend(
        _reference_delta(metric) for metric in TEAM_REFERENCE_METRICS
    )
    expressions.extend(
        _period_delta(metric) for metric in TEAM_CORE_PERIOD_METRICS
    )
    expressions.extend(_additional_team_deltas())
    if include_period_combined:
        expressions.append(_derived_period_delta())
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_team_distance_absolute AS absolute
LEFT JOIN v_team_distance_reference AS reference
    ON reference.season_id IS NOT DISTINCT FROM absolute.season_id
   AND reference.team_id IS NOT DISTINCT FROM absolute.team_id
"""


def _player_delta_query(include_period_combined: bool) -> str:
    expressions = [f"absolute.{column}" for column in PLAYER_IDENTIFIERS]
    expressions.extend(
        _reference_delta(metric) for metric in PLAYER_DELTA_METRICS
    )
    expressions.extend(
        _period_delta(metric) for metric in PLAYER_PERIOD_METRICS
    )
    if include_period_combined:
        expressions.append(_derived_period_delta())
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_player_distance_absolute AS absolute
LEFT JOIN v_player_distance_reference AS reference
    ON reference.season_id IS NOT DISTINCT FROM absolute.season_id
   AND reference.player_id IS NOT DISTINCT FROM absolute.player_id
"""


def _replace_delta_views(include_period_combined: bool) -> None:
    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute("DROP VIEW v_player_distance_summary")
    op.execute("DROP VIEW v_player_distance_deltas")
    op.execute(
        "CREATE VIEW v_team_distance_deltas AS "
        + _team_delta_query(include_period_combined)
    )
    op.execute(
        "CREATE VIEW v_team_distance_summary AS "
        "SELECT * FROM v_team_distance_deltas"
    )
    op.execute(
        "CREATE VIEW v_player_distance_deltas AS "
        + _player_delta_query(include_period_combined)
    )
    op.execute(
        "CREATE VIEW v_player_distance_summary AS "
        "SELECT * FROM v_player_distance_deltas"
    )


def upgrade() -> None:
    _replace_delta_views(include_period_combined=True)


def downgrade() -> None:
    _replace_delta_views(include_period_combined=False)
