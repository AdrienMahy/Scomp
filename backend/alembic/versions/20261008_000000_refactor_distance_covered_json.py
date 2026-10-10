"""Refactor team and player distance data into match and interval JSONB nodes.

Revision ID: 20261008_000000
Revises: 20260924_000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261008_000000"
down_revision = "20260924_000000"
branch_labels = None
depends_on = None


DISTANCE_TABLES = (
    ("team_distance_covered", False),
    ("player_distance_covered", True),
)


def _legacy_interval_json(table: str) -> str:
    return f"""
        SELECT COALESCE(
            jsonb_object_agg(
                interval_entry.key,
                jsonb_build_object(
                    'total_distance_m', interval_entry.value,
                    'speed_zones_m', NULL
                )
            ),
            '{{}}'::jsonb
        )
        FROM jsonb_each(
            CASE
                WHEN jsonb_typeof(time_intervals::jsonb) = 'object'
                    THEN time_intervals::jsonb
                ELSE '{{}}'::jsonb
            END
        ) AS interval_entry
    """


def _period_total_sql(keys: tuple[str, ...]) -> str:
    sql_keys = ", ".join("'" + key + "'" for key in keys)
    return f"""
        (
            SELECT SUM(interval_entry.value::numeric)
            FROM jsonb_each_text(
                CASE
                    WHEN jsonb_typeof(time_intervals::jsonb) = 'object'
                        THEN time_intervals::jsonb
                    ELSE '{{}}'::jsonb
                END
            ) AS interval_entry
            WHERE interval_entry.key IN ({sql_keys})
        )
    """


def _backfill_table(table: str, is_player: bool) -> None:
    player_metrics = ""
    if is_player:
        player_metrics = """
            || jsonb_strip_nulls(jsonb_build_object(
                'minutes_played', metrics::jsonb->'minutes_played',
                'distance_per_min_played_m',
                    metrics::jsonb->'distance_per_min_played_m'
            ))
        """

    mt1_total = _period_total_sql(
        ("0_5", "5_10", "10_15", "15_20", "20_25", "25_30",
         "30_35", "35_40", "40_45", "45+")
    )
    mt2_total = _period_total_sql(
        ("45_50", "50_55", "55_60", "60_65", "65_70", "70_75",
         "75_80", "80_85", "85_90", "90+")
    )
    op.execute(
        f"""
        UPDATE {table}
        SET match_data =
            jsonb_build_object(
                'total_distance_m', metrics::jsonb->'total_distance_m',
                'speed_zones_m', COALESCE(speed_zones::jsonb, '{{}}'::jsonb),
                'game_state_m', COALESCE(game_state::jsonb, '{{}}'::jsonb),
                'game_state_by_speed_zone_m', '{{}}'::jsonb,
                'periods', jsonb_build_object(
                    'MT1', jsonb_build_object(
                        'total_distance_m', {mt1_total},
                        'speed_zones_m', NULL
                    ),
                    'MT2', jsonb_build_object(
                        'total_distance_m', {mt2_total},
                        'speed_zones_m', NULL
                    )
                )
            )
            {player_metrics},
            intervals = ({_legacy_interval_json(table)})
        """
    )


def _create_views() -> None:
    op.execute("""
    CREATE VIEW v_team_distance_summary AS
    WITH match_rows AS (
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
    )
    SELECT
        match_rows.*,
        MAX(total_distance_m) OVER team_season AS season_max_total_distance_m,
        ROUND(AVG(total_distance_m) OVER team_season, 2)
            AS season_avg_total_distance_m,
        MAX(high_intensity_m) OVER team_season AS season_max_high_intensity_m,
        ROUND(AVG(high_intensity_m) OVER team_season, 2)
            AS season_avg_high_intensity_m,
        MAX(sprint_m) OVER team_season AS season_max_sprint_m,
        ROUND(AVG(sprint_m) OVER team_season, 2) AS season_avg_sprint_m,
        MAX(mt1_total_distance_m) OVER team_season AS season_max_mt1_total_distance_m,
        ROUND(AVG(mt1_total_distance_m) OVER team_season, 2)
            AS season_avg_mt1_total_distance_m,
        MAX(mt1_high_intensity_m) OVER team_season
            AS season_max_mt1_high_intensity_m,
        ROUND(AVG(mt1_high_intensity_m) OVER team_season, 2)
            AS season_avg_mt1_high_intensity_m,
        MAX(mt1_sprint_m) OVER team_season AS season_max_mt1_sprint_m,
        ROUND(AVG(mt1_sprint_m) OVER team_season, 2)
            AS season_avg_mt1_sprint_m,
        MAX(mt2_total_distance_m) OVER team_season AS season_max_mt2_total_distance_m,
        ROUND(AVG(mt2_total_distance_m) OVER team_season, 2)
            AS season_avg_mt2_total_distance_m,
        MAX(mt2_high_intensity_m) OVER team_season
            AS season_max_mt2_high_intensity_m,
        ROUND(AVG(mt2_high_intensity_m) OVER team_season, 2)
            AS season_avg_mt2_high_intensity_m,
        MAX(mt2_sprint_m) OVER team_season AS season_max_mt2_sprint_m,
        ROUND(AVG(mt2_sprint_m) OVER team_season, 2)
            AS season_avg_mt2_sprint_m
    FROM match_rows
    WINDOW team_season AS (PARTITION BY season_id, team_id)
    """)

    op.execute("""
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
    """)

    op.execute("""
    CREATE VIEW v_player_distance_by_speed_zone AS
    SELECT
        g.name AS game_name,
        p.name AS player_name,
        t.name AS team_name,
        zone.key AS speed_zone,
        zone.value::double precision AS distance_m,
        ROUND((d.match_data->>'total_distance_m')::numeric, 2)
            AS total_distance_m,
        ROUND((d.match_data->>'distance_per_min_played_m')::numeric, 2)
            AS distance_per_min_played_m,
        ROUND((d.match_data->>'minutes_played')::numeric, 2)
            AS minutes_played
    FROM player_distance_covered d
    JOIN games g ON d.game_id = g.id
    JOIN players p ON d.player_id = p.id
    JOIN teams t ON d.team_id = t.id
    CROSS JOIN LATERAL jsonb_each_text(d.match_data->'speed_zones_m') AS zone
    """)

    op.execute("""
    CREATE VIEW v_player_distance_by_zone_interval AS
    SELECT
        ROUND((d.match_data->>'total_distance_m')::numeric, 2)
            AS total_distance_m,
        zone.key AS speed_zone,
        interval_entry.key AS time_interval,
        p.name AS player_name,
        g.name AS game_name,
        t.name AS team_name,
        zone.value::double precision AS interval_distance_m
    FROM player_distance_covered d
    JOIN games g ON d.game_id = g.id
    JOIN players p ON d.player_id = p.id
    JOIN teams t ON d.team_id = t.id
    CROSS JOIN LATERAL jsonb_each(d.intervals) AS interval_entry
    CROSS JOIN LATERAL jsonb_each_text(
        interval_entry.value->'speed_zones_m'
    ) AS zone
    """)


def _create_legacy_views() -> None:
    op.execute("""
    CREATE VIEW v_player_distance_summary AS
    SELECT
        d.game_id,
        d.player_id,
        d.team_id,
        g.name AS game_name,
        p.name AS player_name,
        t.name AS team_name,
        ROUND((d.metrics->>'total_distance_m')::numeric, 2) AS total_distance_m,
        ROUND((d.metrics->>'minutes_played')::numeric, 2) AS minutes_played
    FROM player_distance_covered d
    LEFT JOIN games g ON d.game_id = g.id
    LEFT JOIN players p ON d.player_id = p.id
    LEFT JOIN teams t ON d.team_id = t.id
    """)

    op.execute("""
    CREATE VIEW v_team_distance_summary AS
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
        (d.metrics->>'total_distance_m')::numeric AS total_distance_m,
        (d.metrics->>'minutes_played')::numeric AS minutes_played,
        (d.speed_zones->>'walking')::numeric AS walking_m,
        (d.speed_zones->>'jogging')::numeric AS jogging_m,
        (d.speed_zones->>'moderated_intensity')::numeric AS moderated_intensity_m,
        (d.speed_zones->>'high_intensity')::numeric AS high_intensity_m,
        (d.speed_zones->>'sprint')::numeric AS sprint_m,
        (
            (d.speed_zones->>'high_intensity')::numeric
            + (d.speed_zones->>'sprint')::numeric
        ) AS high_intensity_distance_m,
        (
            (d.speed_zones->>'walking')::numeric
            + (d.speed_zones->>'jogging')::numeric
        ) AS low_intensity_distance_m,
        CASE
            WHEN (d.metrics->>'total_distance_m')::numeric > 0
            THEN ROUND((
                (
                    (d.speed_zones->>'high_intensity')::numeric
                    + (d.speed_zones->>'sprint')::numeric
                ) / (d.metrics->>'total_distance_m')::numeric * 100
            ), 2)
            ELSE NULL
        END AS high_intensity_ratio_percent,
        ROUND(((d.metrics->>'total_distance_m')::numeric / 90), 2)
            AS avg_speed_m_per_minute,
        d.created_at,
        d.updated_at,
        d.metrics AS full_metrics_jsonb,
        d.speed_zones AS full_speed_zones_jsonb,
        d.game_state AS full_game_state_jsonb,
        d.time_intervals AS full_time_intervals_jsonb
    FROM team_distance_covered d
    LEFT JOIN games g ON d.game_id::text = g.id::text
    LEFT JOIN teams t ON d.team_id::text = t.id::text
    """)

    op.execute("""
    CREATE VIEW v_player_distance_by_speed_zone AS
    SELECT
        g.name AS game_name,
        p.name AS player_name,
        t.name AS team_name,
        zone.key AS speed_zone,
        zone.value::double precision AS distance_m,
        ROUND((d.metrics->>'total_distance_m')::numeric, 2) AS total_distance_m,
        ROUND((d.metrics->>'distance_per_min_played_m')::numeric, 2)
            AS distance_per_min_played_m,
        ROUND((d.metrics->>'minutes_played')::numeric, 2) AS minutes_played
    FROM player_distance_covered d
    JOIN games g ON d.game_id = g.id
    JOIN players p ON d.player_id = p.id
    JOIN teams t ON d.team_id = t.id
    CROSS JOIN LATERAL jsonb_each_text(d.speed_zones::jsonb) AS zone
    """)

    op.execute("""
    CREATE VIEW v_player_distance_by_zone_interval AS
    SELECT
        ROUND((d.metrics->>'total_distance_m')::numeric, 2) AS total_distance_m,
        zone.key AS speed_zone,
        interval_entry.key AS time_interval,
        p.name AS player_name,
        g.name AS game_name,
        t.name AS team_name
    FROM player_distance_covered d
    JOIN games g ON d.game_id = g.id
    JOIN players p ON d.player_id = p.id
    JOIN teams t ON d.team_id = t.id
    LEFT JOIN LATERAL jsonb_each_text(d.speed_zones::jsonb) AS zone ON TRUE
    LEFT JOIN LATERAL jsonb_each_text(d.time_intervals::jsonb)
        AS interval_entry ON TRUE
    """)


def upgrade() -> None:
    for view in (
        "v_player_distance_summary",
        "v_team_distance_summary",
        "v_player_distance_by_speed_zone",
        "v_player_distance_by_zone_interval",
    ):
        op.execute(f"DROP VIEW IF EXISTS {view}")

    for table, is_player in DISTANCE_TABLES:
        op.add_column(
            table,
            sa.Column(
                "match_data",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "intervals",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
        _backfill_table(table, is_player)

    for table in ("team_distance_covered", "player_distance_covered"):
        op.execute(
            f"DROP INDEX IF EXISTS ix_{table}_time_intervals"
        )
        for column in ("metrics", "speed_zones", "game_state", "time_intervals"):
            op.drop_column(table, column)
        op.create_index(
            f"ix_{table}_match_data",
            table,
            ["match_data"],
            postgresql_using="gin",
        )
        op.create_index(
            f"ix_{table}_intervals",
            table,
            ["intervals"],
            postgresql_using="gin",
        )

    _create_views()


def downgrade() -> None:
    for view in (
        "v_player_distance_summary",
        "v_team_distance_summary",
        "v_player_distance_by_speed_zone",
        "v_player_distance_by_zone_interval",
    ):
        op.execute(f"DROP VIEW IF EXISTS {view}")

    for table, _ in DISTANCE_TABLES:
        op.drop_index(f"ix_{table}_match_data", table_name=table)
        op.drop_index(f"ix_{table}_intervals", table_name=table)
        for column, column_type in (
            ("metrics", sa.JSON()),
            ("speed_zones", sa.JSON()),
            ("game_state", sa.JSON()),
            ("time_intervals", postgresql.JSONB(astext_type=sa.Text())),
        ):
            op.add_column(
                table,
                sa.Column(column, column_type, nullable=True),
            )

        op.execute(f"""
            UPDATE {table}
            SET metrics = jsonb_build_object(
                    'total_distance_m', match_data->'total_distance_m',
                    'minutes_played', match_data->'minutes_played',
                    'distance_per_min_played_m',
                        match_data->'distance_per_min_played_m'
                )::json,
                speed_zones = (match_data->'speed_zones_m')::json,
                game_state = (match_data->'game_state_m')::json,
                time_intervals = (
                    SELECT COALESCE(
                        jsonb_object_agg(
                            interval_entry.key,
                            interval_entry.value->'total_distance_m'
                        ),
                        '{{}}'::jsonb
                    )
                    FROM jsonb_each(intervals) AS interval_entry
                )
        """)
        for column in ("metrics", "speed_zones", "game_state", "time_intervals"):
            op.alter_column(table, column, nullable=False)

        op.drop_column(table, "match_data")
        op.drop_column(table, "intervals")
        op.create_index(
            f"ix_{table}_time_intervals",
            table,
            ["time_intervals"],
            postgresql_using="gin",
        )

    _create_legacy_views()
