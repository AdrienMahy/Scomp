"""Expose the first-contact cross indicator in v_corners.

Revision ID: 20261012_100000
Revises: 20261012_090000
"""

from alembic import op


revision = "20261012_100000"
down_revision = "20261012_090000"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
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
    sp.corner_kick->>'effect' AS corner_effect,
    CASE
        WHEN sp.corner_kick->>'first_contact_is_goal' = 'true' THEN 'Goal'
        WHEN sp.corner_kick->>'first_contact_is_shot' = 'true' THEN 'Shot'
        WHEN sp.corner_kick->>'first_contact_is_goal' = 'false'
         AND sp.corner_kick->>'first_contact_is_shot' = 'false'
         AND sp.corner_kick->>'offensive_first_contact' = 'true' THEN 'Offensive'
        WHEN sp.corner_kick->>'gk_first_contact' = 'true' THEN 'Goalkeeper'
    END AS first_contact,
    CASE
        WHEN sp.corner_kick->>'second_contact_is_shot' = 'true' THEN 'Shot'
        WHEN sp.corner_kick->>'offensive_second_contact' = 'true' THEN 'Offensive'
    END AS second_contact,
    CASE
        WHEN sp.corner_kick->>'first_contact_is_cross' IN ('true', 'false')
        THEN (sp.corner_kick->>'first_contact_is_cross')::boolean
    END AS first_contact_is_cross
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
DO $$
DECLARE
    corner_actors_definition text;
    corner_strategy_definition text;
BEGIN
    SELECT pg_get_viewdef('public.v_corner_actors'::regclass, true)
    INTO corner_actors_definition;
    SELECT pg_get_viewdef('public.v_corner_strategy'::regclass, true)
    INTO corner_strategy_definition;

    DROP VIEW public.v_corner_strategy;
    DROP VIEW public.v_corner_actors;
    DROP VIEW public.v_corners;

    EXECUTE $create_corners$
        CREATE VIEW public.v_corners AS
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
            sp.corner_kick->>'effect' AS corner_effect,
            CASE
                WHEN sp.corner_kick->>'first_contact_is_goal' = 'true' THEN 'Goal'
                WHEN sp.corner_kick->>'first_contact_is_shot' = 'true' THEN 'Shot'
                WHEN sp.corner_kick->>'first_contact_is_goal' = 'false'
                 AND sp.corner_kick->>'first_contact_is_shot' = 'false'
                 AND sp.corner_kick->>'offensive_first_contact' = 'true' THEN 'Offensive'
                WHEN sp.corner_kick->>'gk_first_contact' = 'true' THEN 'Goalkeeper'
            END AS first_contact,
            CASE
                WHEN sp.corner_kick->>'second_contact_is_shot' = 'true' THEN 'Shot'
                WHEN sp.corner_kick->>'offensive_second_contact' = 'true' THEN 'Offensive'
            END AS second_contact
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
    $create_corners$;

    EXECUTE 'CREATE VIEW public.v_corner_actors AS '
        || corner_actors_definition;
    EXECUTE 'CREATE VIEW public.v_corner_strategy AS '
        || corner_strategy_definition;
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
