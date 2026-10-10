"""Add high-intensity composite and ratio season references.

Revision ID: 20261008_080000
Revises: 20261008_070000
"""

from alembic import op
from sqlalchemy import text


revision = "20261008_080000"
down_revision = "20261008_070000"
branch_labels = None
depends_on = None


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

DERIVED_REFERENCE_METRICS = (
    "high_intensity_distance_m",
    "high_intensity_ratio_percent",
)


def _reference_column(metric: str, stat: str) -> str:
    if metric.endswith("_percent"):
        suffix = metric.removesuffix("_percent")
        unit = "percent"
    else:
        suffix = metric.removesuffix("_m")
        unit = "m"
    return f"season_{stat}_{suffix}_{unit}"


def _reference_expressions(metrics: tuple[str, ...]) -> list[str]:
    expressions = []
    for metric in metrics:
        max_column = _reference_column(metric, "max")
        avg_column = _reference_column(metric, "avg")
        expressions.extend(
            (
                f"MAX(absolute.{metric}) AS {max_column}",
                f"ROUND(AVG(absolute.{metric}), 2) AS {avg_column}",
            )
        )
    return expressions


def _reference_view(include_derived_metrics: bool) -> str:
    metrics = REFERENCE_METRICS
    if include_derived_metrics:
        metrics += DERIVED_REFERENCE_METRICS

    expressions = [
        "absolute.season_id",
        "absolute.team_id",
        "MAX(absolute.team_name) AS team_name",
        "MAX(absolute.team_brand) AS team_brand",
    ]
    expressions.extend(_reference_expressions(metrics))
    select_list = ",\n    ".join(expressions)
    return f"""
CREATE OR REPLACE VIEW v_team_distance_reference AS
SELECT
    {select_list}
FROM v_team_distance_absolute AS absolute
GROUP BY absolute.season_id, absolute.team_id
"""


def upgrade() -> None:
    op.execute(_reference_view(include_derived_metrics=True))


def downgrade() -> None:
    connection = op.get_bind()
    deltas_definition = connection.execute(
        text(
            "SELECT pg_get_viewdef("
            "CAST('v_team_distance_deltas' AS regclass), true)"
        )
    ).scalar_one()
    summary_definition = connection.execute(
        text(
            "SELECT pg_get_viewdef("
            "CAST('v_team_distance_summary' AS regclass), true)"
        )
    ).scalar_one()

    op.execute("DROP VIEW v_team_distance_summary")
    op.execute("DROP VIEW v_team_distance_deltas")
    op.execute("DROP VIEW v_team_distance_reference")
    op.execute(_reference_view(include_derived_metrics=False))
    op.execute(
        "CREATE VIEW v_team_distance_deltas AS " + deltas_definition
    )
    op.execute(
        "CREATE VIEW v_team_distance_summary AS " + summary_definition
    )
