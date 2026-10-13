"""Expose outcome_detail instead of outcome in corner views.

Revision ID: 20261012_080000
Revises: 20261012_070000
"""

from alembic import op


revision = "20261012_080000"
down_revision = "20261012_070000"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
ALTER VIEW v_corners RENAME COLUMN outcome TO outcome_detail;
ALTER VIEW v_corner_strategy RENAME COLUMN outcome TO outcome_detail;

CREATE OR REPLACE VIEW v_corners AS
SELECT
    sp.id AS corner_id,
    sp.entity->>'sequence_id' AS sequence_id,
    sp.game_id,
    g.name AS game_name,
    COALESCE(g.round_name, g.round) AS round,
    sp.team_id,
    team.name AS team_name,
    sp.opponent_team_id,
    opponent.name AS opponent_team_name,
    COALESCE(sp.player_id, sp.actors->>'taker') AS taker_id,
    taker.name AS taker_name,
    sp.period_id AS period,
    sp.corner_kick->>'quarter' AS quarter,
    sp.spatial->>'side' AS side,
    CASE
        WHEN sp.corner_kick->>'short_corner' IN ('true', 'false')
        THEN (sp.corner_kick->>'short_corner')::boolean
    END AS short_corner,
    sp.corner_kick->>'outcome_detail' AS outcome_detail,
    CASE
        WHEN sp.corner_kick->>'goal_in_sequence' IN ('true', 'false')
        THEN (sp.corner_kick->>'goal_in_sequence')::boolean
    END AS goal_in_sequence,
    sp.corner_kick->>'pass' AS pass_sequence_id,
    CASE
        WHEN jsonb_typeof(pass_event.entity->'end_x') = 'number'
        THEN (pass_event.entity->>'end_x')::double precision
    END AS arrival_x,
    CASE
        WHEN jsonb_typeof(pass_event.entity->'end_y') = 'number'
        THEN (pass_event.entity->>'end_y')::double precision
    END AS arrival_y,
    sp.corner_kick->>'effect' AS corner_effect
FROM setpieces AS sp
JOIN games AS g
    ON g.id = sp.game_id
LEFT JOIN teams AS team
    ON team.id = sp.team_id
LEFT JOIN teams AS opponent
    ON opponent.id = sp.opponent_team_id
LEFT JOIN players AS taker
    ON taker.id = COALESCE(sp.player_id, sp.actors->>'taker')
LEFT JOIN events AS pass_event
    ON pass_event.game_id = sp.game_id
   AND pass_event.entity->>'sequence_id' = sp.corner_kick->>'pass'
   AND lower(pass_event.entity->>'gata_display_name') = 'pass'
WHERE lower(trim(replace(sp.gata_display_name, '-', ' '))) = 'corner kick'
"""


DOWNGRADE_SQL = """
ALTER VIEW v_corners RENAME COLUMN outcome_detail TO outcome;
ALTER VIEW v_corner_strategy RENAME COLUMN outcome_detail TO outcome;

CREATE OR REPLACE VIEW v_corners AS
SELECT
    sp.id AS corner_id,
    sp.entity->>'sequence_id' AS sequence_id,
    sp.game_id,
    g.name AS game_name,
    COALESCE(g.round_name, g.round) AS round,
    sp.team_id,
    team.name AS team_name,
    sp.opponent_team_id,
    opponent.name AS opponent_team_name,
    COALESCE(sp.player_id, sp.actors->>'taker') AS taker_id,
    taker.name AS taker_name,
    sp.period_id AS period,
    sp.corner_kick->>'quarter' AS quarter,
    sp.spatial->>'side' AS side,
    CASE
        WHEN sp.corner_kick->>'short_corner' IN ('true', 'false')
        THEN (sp.corner_kick->>'short_corner')::boolean
    END AS short_corner,
    sp.corner_kick->>'outcome' AS outcome,
    CASE
        WHEN sp.corner_kick->>'goal_in_sequence' IN ('true', 'false')
        THEN (sp.corner_kick->>'goal_in_sequence')::boolean
    END AS goal_in_sequence,
    sp.corner_kick->>'pass' AS pass_sequence_id,
    CASE
        WHEN jsonb_typeof(pass_event.entity->'end_x') = 'number'
        THEN (pass_event.entity->>'end_x')::double precision
    END AS arrival_x,
    CASE
        WHEN jsonb_typeof(pass_event.entity->'end_y') = 'number'
        THEN (pass_event.entity->>'end_y')::double precision
    END AS arrival_y,
    sp.corner_kick->>'effect' AS corner_effect
FROM setpieces AS sp
JOIN games AS g
    ON g.id = sp.game_id
LEFT JOIN teams AS team
    ON team.id = sp.team_id
LEFT JOIN teams AS opponent
    ON opponent.id = sp.opponent_team_id
LEFT JOIN players AS taker
    ON taker.id = COALESCE(sp.player_id, sp.actors->>'taker')
LEFT JOIN events AS pass_event
    ON pass_event.game_id = sp.game_id
   AND pass_event.entity->>'sequence_id' = sp.corner_kick->>'pass'
   AND lower(pass_event.entity->>'gata_display_name') = 'pass'
WHERE lower(trim(replace(sp.gata_display_name, '-', ' '))) = 'corner kick'
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
