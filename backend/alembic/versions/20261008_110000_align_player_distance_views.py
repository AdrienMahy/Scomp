"""Align player distance references and deltas with team distance views.

Revision ID: 20261008_110000
Revises: 20261008_100000
"""

from alembic import op


revision = "20261008_110000"
down_revision = "20261008_100000"
branch_labels = None
depends_on = None


BASE_PLAYER_COLUMNS = (
    "game_id",
    "player_id",
    "team_id",
    "game_name",
    "player_name",
    "team_name",
    "total_distance_m",
    "minutes_played",
    "distance_per_min_played_m",
    "mt1_total_distance_m",
    "mt2_total_distance_m",
    "full_match_data_jsonb",
    "full_intervals_jsonb",
    "season_id",
    "game_round_name",
    "high_intensity_m",
    "sprint_m",
    "mt1_high_intensity_m",
    "mt1_sprint_m",
    "mt2_high_intensity_m",
    "mt2_sprint_m",
)

ADDED_PLAYER_COLUMNS = (
    "walking_m",
    "jogging_m",
    "moderated_intensity_m",
    "high_intensity_distance_m",
    "high_intensity_ratio_percent",
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
    "high_intensity_distance_m",
    "high_intensity_ratio_percent",
)

DELTA_METRICS = (
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

PERIOD_DELTA_METRICS = (
    ("total_distance_m", "total_distance"),
    ("walking_m", "walking"),
    ("jogging_m", "jogging"),
    ("moderated_intensity_m", "moderated_intensity"),
    ("high_intensity_m", "high_intensity"),
    ("sprint_m", "sprint"),
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

LEGACY_DELTA_METRICS = LEGACY_REFERENCE_METRICS
LEGACY_PERIOD_DELTA_METRICS = (
    ("mt1_total_distance_m", "mt2_total_distance_m", "total_distance"),
    ("mt1_high_intensity_m", "mt2_high_intensity_m", "high_intensity"),
    ("mt1_sprint_m", "mt2_sprint_m", "sprint"),
)

LEGACY_ABSOLUTE_EXPRESSIONS = (
    "d.game_id",
    "d.player_id",
    "d.team_id",
    "g.name AS game_name",
    "p.name AS player_name",
    "t.name AS team_name",
    """ROUND((d.match_data->>'total_distance_m')::numeric, 2)
        AS total_distance_m""",
    """ROUND((d.match_data->>'minutes_played')::numeric, 2)
        AS minutes_played""",
    """ROUND((d.match_data->>'distance_per_min_played_m')::numeric, 2)
        AS distance_per_min_played_m""",
    """(d.match_data->'periods'->'MT1'->>'total_distance_m')::numeric
        AS mt1_total_distance_m""",
    """(d.match_data->'periods'->'MT2'->>'total_distance_m')::numeric
        AS mt2_total_distance_m""",
    "d.match_data AS full_match_data_jsonb",
    "d.intervals AS full_intervals_jsonb",
    "g.season_id AS season_id",
    "g.round_name AS game_round_name",
    """(d.match_data->'speed_zones_m'->>'high_intensity')::numeric
        AS high_intensity_m""",
    """(d.match_data->'speed_zones_m'->>'sprint')::numeric AS sprint_m""",
    """(d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'high_intensity')::numeric AS mt1_high_intensity_m""",
    """(d.match_data->'periods'->'MT1'->'speed_zones_m'
        ->>'sprint')::numeric AS mt1_sprint_m""",
    """(d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'high_intensity')::numeric AS mt2_high_intensity_m""",
    """(d.match_data->'periods'->'MT2'->'speed_zones_m'
        ->>'sprint')::numeric AS mt2_sprint_m""",
)

ADDED_ABSOLUTE_EXPRESSIONS = (
    """(d.match_data->'speed_zones_m'->>'walking')::numeric
        AS walking_m""",
    """(d.match_data->'speed_zones_m'->>'jogging')::numeric
        AS jogging_m""",
    """(d.match_data->'speed_zones_m'->>'moderated_intensity')::numeric
        AS moderated_intensity_m""",
    """(
        (d.match_data->'speed_zones_m'->>'high_intensity')::numeric
        + (d.match_data->'speed_zones_m'->>'sprint')::numeric
    ) AS high_intensity_distance_m""",
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

LEGACY_REFERENCE_EXPRESSIONS = (
    ("total_distance_m", "season_max_total_distance_m",
     "season_avg_total_distance_m"),
    ("high_intensity_m", "season_max_high_intensity_m",
     "season_avg_high_intensity_m"),
    ("sprint_m", "season_max_sprint_m", "season_avg_sprint_m"),
    ("mt1_total_distance_m", "season_max_mt1_total_distance_m",
     "season_avg_mt1_total_distance_m"),
    ("mt1_high_intensity_m", "season_max_mt1_high_intensity_m",
     "season_avg_mt1_high_intensity_m"),
    ("mt1_sprint_m", "season_max_mt1_sprint_m", "season_avg_mt1_sprint_m"),
    ("mt2_total_distance_m", "season_max_mt2_total_distance_m",
     "season_avg_mt2_total_distance_m"),
    ("mt2_high_intensity_m", "season_max_mt2_high_intensity_m",
     "season_avg_mt2_high_intensity_m"),
    ("mt2_sprint_m", "season_max_mt2_sprint_m", "season_avg_mt2_sprint_m"),
)


def _metric_suffix(metric: str) -> str:
    return metric[:-2] if metric.endswith("_m") else metric


def _season_column(metric: str, stat: str) -> str:
    if metric.endswith("_percent"):
        suffix = metric.removesuffix("_percent")
        unit = "percent"
    else:
        suffix = _metric_suffix(metric)
        unit = "m"
    return f"season_{stat}_{suffix}_{unit}"


def _reference_expressions(
    alias: str,
    metrics: tuple[str, ...],
    grouped: bool,
) -> list[str]:
    expressions = []
    for metric in metrics:
        max_column = _season_column(metric, "max")
        avg_column = _season_column(metric, "avg")
        if grouped:
            expressions.extend(
                (
                    f"MAX({alias}.{metric}) AS {max_column}",
                    f"ROUND(AVG({alias}.{metric}), 2) AS {avg_column}",
                )
            )
        else:
            expressions.extend(
                (
                    f"MAX({alias}.{metric}) OVER player_season "
                    f"AS {max_column}",
                    f"ROUND(AVG({alias}.{metric}) OVER player_season, 2) "
                    f"AS {avg_column}",
                )
            )
    return expressions


def _absolute_query(include_added_metrics: bool) -> str:
    expressions = list(LEGACY_ABSOLUTE_EXPRESSIONS)
    if include_added_metrics:
        expressions.extend(ADDED_ABSOLUTE_EXPRESSIONS)
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM player_distance_covered d
LEFT JOIN games g ON d.game_id = g.id
LEFT JOIN players p ON d.player_id = p.id
LEFT JOIN teams t ON d.team_id = t.id
"""


def _grouped_reference_query() -> str:
    expressions = [
        "absolute.season_id",
        "absolute.player_id",
        "MAX(absolute.player_name) AS player_name",
    ]
    expressions.extend(
        _reference_expressions(
            "absolute",
            REFERENCE_METRICS,
            grouped=True,
        )
    )
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_player_distance_absolute AS absolute
GROUP BY absolute.season_id, absolute.player_id
"""


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
            f"- {reference_alias}.{_season_column(metric, 'avg')}, 2) "
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


def _grouped_delta_query() -> str:
    expressions = [f"absolute.{column}" for column in PLAYER_IDENTIFIERS]
    expressions.extend(
        _delta_expressions("absolute", "reference", DELTA_METRICS)
    )
    expressions.extend(
        _period_delta_expressions("absolute", tuple(
            metric for metric, _ in PERIOD_DELTA_METRICS
        ))
    )
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_player_distance_absolute AS absolute
LEFT JOIN v_player_distance_reference AS reference
    ON reference.season_id IS NOT DISTINCT FROM absolute.season_id
   AND reference.player_id IS NOT DISTINCT FROM absolute.player_id
"""


def _relative_query() -> str:
    return """
SELECT
    absolute.*,
    ROUND(total_distance_m / NULLIF(minutes_played, 0), 2)
        AS total_distance_per_min_played_m,
    ROUND(high_intensity_m / NULLIF(minutes_played, 0), 2)
        AS high_intensity_per_min_played_m,
    ROUND(sprint_m / NULLIF(minutes_played, 0), 2)
        AS sprint_per_min_played_m
FROM v_player_distance_absolute AS absolute
"""


def _legacy_reference_query() -> str:
    expressions = ["absolute.*"]
    metrics = LEGACY_REFERENCE_METRICS
    for metric, max_column, avg_column in LEGACY_REFERENCE_EXPRESSIONS:
        expressions.extend(
            (
                f"MAX(absolute.{metric}) OVER player_season AS {max_column}",
                f"ROUND(AVG(absolute.{metric}) OVER player_season, 2) "
                f"AS {avg_column}",
            )
        )
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_player_distance_absolute AS absolute
WINDOW player_season AS (
    PARTITION BY absolute.season_id, absolute.player_id
)
"""


def _legacy_delta_query() -> str:
    expressions = ["reference.*"]
    for metric, max_column, avg_column in LEGACY_REFERENCE_EXPRESSIONS:
        suffix = _metric_suffix(metric)
        expressions.append(
            f"ROUND(reference.{metric} - reference.{avg_column}, 2) "
            f"AS delta_{suffix}_m"
        )
    for mt1_metric, mt2_metric, suffix in LEGACY_PERIOD_DELTA_METRICS:
        expressions.append(
            f"ROUND(reference.{mt1_metric} - reference.{mt2_metric}, 2) "
            f"AS delta_period_{suffix}_m"
        )
    select_list = ",\n    ".join(expressions)
    return f"""
SELECT
    {select_list}
FROM v_player_distance_reference AS reference
"""


def _legacy_relative_query() -> str:
    return f"""
SELECT
    absolute.*,
    ROUND(total_distance_m / NULLIF(minutes_played, 0), 2)
        AS total_distance_per_min_played_m,
    ROUND(high_intensity_m / NULLIF(minutes_played, 0), 2)
        AS high_intensity_per_min_played_m,
    ROUND(sprint_m / NULLIF(minutes_played, 0), 2)
        AS sprint_per_min_played_m
FROM v_player_distance_absolute AS absolute
"""


def _create_legacy_views() -> None:
    op.execute(f"CREATE VIEW v_player_distance_absolute AS {_absolute_query(False)}")
    op.execute(
        "CREATE VIEW v_player_distance_reference AS "
        + _legacy_reference_query()
    )
    op.execute(
        "CREATE VIEW v_player_distance_deltas AS "
        + _legacy_delta_query()
    )
    op.execute(
        "CREATE VIEW v_player_distance_relative AS "
        + _legacy_relative_query()
    )
    op.execute(
        "CREATE VIEW v_player_distance_summary AS "
        "SELECT * FROM v_player_distance_deltas"
    )


def upgrade() -> None:
    op.execute("DROP VIEW v_player_distance_summary")
    op.execute("DROP VIEW v_player_distance_deltas")
    op.execute("DROP VIEW v_player_distance_reference")
    op.execute("DROP VIEW v_player_distance_relative")
    op.execute("DROP VIEW v_player_distance_absolute")
    op.execute(
        f"CREATE VIEW v_player_distance_absolute AS "
        f"{_absolute_query(include_added_metrics=True)}"
    )
    op.execute(
        "CREATE VIEW v_player_distance_reference AS "
        + _grouped_reference_query()
    )
    op.execute(
        "CREATE VIEW v_player_distance_deltas AS "
        + _grouped_delta_query()
    )
    op.execute(
        "CREATE VIEW v_player_distance_relative AS "
        + _relative_query()
    )
    op.execute(
        "CREATE VIEW v_player_distance_summary AS "
        "SELECT * FROM v_player_distance_deltas"
    )


def downgrade() -> None:
    op.execute("DROP VIEW v_player_distance_summary")
    op.execute("DROP VIEW v_player_distance_deltas")
    op.execute("DROP VIEW v_player_distance_reference")
    op.execute("DROP VIEW v_player_distance_relative")
    op.execute("DROP VIEW v_player_distance_absolute")
    _create_legacy_views()
