"""Read v_goals phase_play from the linked Shot event.

Revision ID: 20261010_030000
Revises: 20261010_020000
"""

from alembic import op


revision = "20261010_030000"
down_revision = "20261010_020000"
branch_labels = None
depends_on = None


VIEW_SQL = """
CREATE OR REPLACE VIEW v_goals AS
SELECT
    go.id AS goal_id,
    g.id AS game_id,
    g.name AS game_name,
    COALESCE(g.round_name, g.round) AS round,
    go.team_id,
    t.name AS team_name,
    go.is_own_goal AS own_goal,
    shot_event.entity->>'phase_of_play_label' AS phase_play,
    go.possession_id,
    type_of_play.entity->>'gata_display_name' AS type,
    shot_event.id AS shot_event_id,
    shot_event.entity->>'outcome' AS shot_outcome,
    CASE
        WHEN jsonb_typeof(shot_event.entity->'xg') = 'number'
        THEN (shot_event.entity->>'xg')::double precision
    END AS shot_xg,
    shot_event.entity->>'body_part' AS shot_body_part,
    CASE
        WHEN jsonb_typeof(shot_event.entity->'start_x') = 'number'
        THEN (shot_event.entity->>'start_x')::double precision
    END AS shot_start_x,
    CASE
        WHEN jsonb_typeof(shot_event.entity->'start_y') = 'number'
        THEN (shot_event.entity->>'start_y')::double precision
    END AS shot_start_y,
    CASE
        WHEN jsonb_typeof(shot_event.entity->'end_x') = 'number'
        THEN (shot_event.entity->>'end_x')::double precision
    END AS shot_end_x,
    CASE
        WHEN jsonb_typeof(shot_event.entity->'end_y') = 'number'
        THEN (shot_event.entity->>'end_y')::double precision
    END AS shot_end_y,
    shot_event.entity AS shot_event
FROM goals AS go
JOIN games AS g
    ON g.id = go.game_id
LEFT JOIN teams AS t
    ON t.id = go.team_id
LEFT JOIN type_of_play
    ON type_of_play.id = go.type_of_play_id::text
   AND type_of_play.game_id = go.game_id
LEFT JOIN events AS shot_event
    ON shot_event.game_id = go.game_id
   AND shot_event.entity->>'sequence_id' = go.shot #>> '{}'
"""


def upgrade() -> None:
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE VIEW v_goals AS
        SELECT
            go.id AS goal_id,
            g.id AS game_id,
            g.name AS game_name,
            COALESCE(g.round_name, g.round) AS round,
            go.team_id,
            t.name AS team_name,
            go.is_own_goal AS own_goal,
            go.phase->>'phase_of_play_label' AS phase_play,
            go.possession_id,
            type_of_play.entity->>'gata_display_name' AS type,
            shot_event.id AS shot_event_id,
            shot_event.entity->>'outcome' AS shot_outcome,
            CASE
                WHEN jsonb_typeof(shot_event.entity->'xg') = 'number'
                THEN (shot_event.entity->>'xg')::double precision
            END AS shot_xg,
            shot_event.entity->>'body_part' AS shot_body_part,
            CASE
                WHEN jsonb_typeof(shot_event.entity->'start_x') = 'number'
                THEN (shot_event.entity->>'start_x')::double precision
            END AS shot_start_x,
            CASE
                WHEN jsonb_typeof(shot_event.entity->'start_y') = 'number'
                THEN (shot_event.entity->>'start_y')::double precision
            END AS shot_start_y,
            CASE
                WHEN jsonb_typeof(shot_event.entity->'end_x') = 'number'
                THEN (shot_event.entity->>'end_x')::double precision
            END AS shot_end_x,
            CASE
                WHEN jsonb_typeof(shot_event.entity->'end_y') = 'number'
                THEN (shot_event.entity->>'end_y')::double precision
            END AS shot_end_y,
            shot_event.entity AS shot_event
        FROM goals AS go
        JOIN games AS g
            ON g.id = go.game_id
        LEFT JOIN teams AS t
            ON t.id = go.team_id
        LEFT JOIN type_of_play
            ON type_of_play.id = go.type_of_play_id::text
           AND type_of_play.game_id = go.game_id
        LEFT JOIN events AS shot_event
            ON shot_event.game_id = go.game_id
           AND shot_event.entity->>'sequence_id' = go.shot #>> '{}'
        """
    )
