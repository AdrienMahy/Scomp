"""Expose the goal period in v_goals.

Revision ID: 20261012_010000
Revises: 20261012_000000
"""

from alembic import op


revision = "20261012_010000"
down_revision = "20261012_000000"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
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
    shot_event.entity AS shot_event,
    COALESCE(shot_event.entity->>'quarter', go.entity->>'quarter') AS quarter,
    COALESCE(go.player_id, go.own_goal_context->>'player_id') AS scorer_id,
    scorer.name AS scorer_name,
    go.opponent_team_id,
    opponent.name AS opponent_team_name,
    go.period_id AS period
FROM goals AS go
JOIN games AS g
    ON g.id = go.game_id
LEFT JOIN teams AS t
    ON t.id = go.team_id
LEFT JOIN players AS scorer
    ON scorer.id = COALESCE(go.player_id, go.own_goal_context->>'player_id')
LEFT JOIN teams AS opponent
    ON opponent.id = go.opponent_team_id
LEFT JOIN type_of_play
    ON type_of_play.id = go.type_of_play_id::text
   AND type_of_play.game_id = go.game_id
LEFT JOIN events AS shot_event
    ON shot_event.game_id = go.game_id
   AND shot_event.entity->>'sequence_id' = go.shot #>> '{}'
"""


DOWNGRADE_SQL = """
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
    shot_event.entity AS shot_event,
    COALESCE(shot_event.entity->>'quarter', go.entity->>'quarter') AS quarter,
    COALESCE(go.player_id, go.own_goal_context->>'player_id') AS scorer_id,
    scorer.name AS scorer_name,
    go.opponent_team_id,
    opponent.name AS opponent_team_name
FROM goals AS go
JOIN games AS g
    ON g.id = go.game_id
LEFT JOIN teams AS t
    ON t.id = go.team_id
LEFT JOIN players AS scorer
    ON scorer.id = COALESCE(go.player_id, go.own_goal_context->>'player_id')
LEFT JOIN teams AS opponent
    ON opponent.id = go.opponent_team_id
LEFT JOIN type_of_play
    ON type_of_play.id = go.type_of_play_id::text
   AND type_of_play.game_id = go.game_id
LEFT JOIN events AS shot_event
    ON shot_event.game_id = go.game_id
   AND shot_event.entity->>'sequence_id' = go.shot #>> '{}'
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
