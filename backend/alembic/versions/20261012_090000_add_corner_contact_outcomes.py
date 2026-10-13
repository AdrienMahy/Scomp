"""Classify first and second contacts in v_corners.

Revision ID: 20261012_090000
Revises: 20261012_080000
"""

from alembic import op


revision = "20261012_090000"
down_revision = "20261012_080000"
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
"""


DOWNGRADE_SQL = """
DROP VIEW v_corner_strategy;
DROP VIEW v_corner_actors;
DROP VIEW v_corners;

CREATE VIEW v_corners AS
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
WHERE lower(trim(replace(sp.gata_display_name, '-', ' '))) = 'corner kick';

CREATE VIEW v_corner_actors AS
WITH corner_setpieces AS (
    SELECT sp.id AS corner_id, sp.actors, sp.corner_kick
    FROM setpieces AS sp
    WHERE lower(trim(replace(sp.gata_display_name, '-', ' '))) = 'corner kick'
),
scalar_roles AS (
    SELECT corner_id, 'taker'::text AS role, actors->>'taker' AS actor_id
    FROM corner_setpieces
    UNION ALL
    SELECT corner_id, 'goalkeeper', actors->>'goalkeeper'
    FROM corner_setpieces
    UNION ALL
    SELECT corner_id, 'first_contact_player', actors->>'first_contact_player'
    FROM corner_setpieces
    UNION ALL
    SELECT corner_id, 'second_contact_player', corner_kick->>'second_contact_player'
    FROM corner_setpieces
),
array_roles AS (
    SELECT cs.corner_id, roles.role, actor.actor_id
    FROM corner_setpieces AS cs
    CROSS JOIN LATERAL (
        VALUES
            ('attackers_at_first_contact', corner_kick->'attackers_at_first_contact'),
            ('attackers_edge_of_the_box', corner_kick->'attackers_edge_of_the_box'),
            ('attackers_far_post', corner_kick->'attackers_far_post'),
            ('attackers_in_6yd_box_at_start', corner_kick->'attackers_in_6yd_box_at_start'),
            ('attackers_in_box', corner_kick->'attackers_in_box'),
            ('attackers_in_box_at_start', corner_kick->'attackers_in_box_at_start'),
            ('attackers_in_central_box', corner_kick->'attackers_in_central_box'),
            ('attackers_near_post', corner_kick->'attackers_near_post'),
            ('defenders_at_first_contact', corner_kick->'defenders_at_first_contact'),
            ('opponent_players_on_pitch', corner_kick->'opponent_players_on_pitch'),
            ('rest_defenders', corner_kick->'rest_defenders'),
            ('short_connectors', corner_kick->'short_connectors'),
            ('team_players_on_pitch', corner_kick->'team_players_on_pitch')
    ) AS roles(role, actor_list)
    CROSS JOIN LATERAL jsonb_array_elements_text(
        CASE
            WHEN jsonb_typeof(roles.actor_list) = 'array' THEN roles.actor_list
            ELSE '[]'::jsonb
        END
    ) AS actor(actor_id)
),
actor_roles AS (
    SELECT corner_id, role, actor_id
    FROM scalar_roles
    WHERE actor_id IS NOT NULL
    UNION ALL
    SELECT corner_id, role, actor_id
    FROM array_roles
    WHERE actor_id IS NOT NULL
)
SELECT DISTINCT
    c.corner_id,
    c.sequence_id,
    c.game_id,
    c.game_name,
    c.round,
    c.period,
    c.quarter,
    c.team_id,
    c.team_name,
    c.opponent_team_id,
    c.opponent_team_name,
    actor_roles.actor_id,
    player.name AS actor_name,
    actor_roles.role
FROM actor_roles
JOIN v_corners AS c
    ON c.corner_id = actor_roles.corner_id
LEFT JOIN players AS player
    ON player.id = actor_roles.actor_id;

CREATE VIEW v_corner_strategy AS
WITH array_roles AS (
    SELECT sp.id AS corner_id, roles.role, actor.actor_id
    FROM setpieces AS sp
    CROSS JOIN LATERAL (
        VALUES
            ('attackers_at_first_contact', sp.corner_kick->'attackers_at_first_contact'),
            ('attackers_edge_of_the_box', sp.corner_kick->'attackers_edge_of_the_box'),
            ('attackers_far_post', sp.corner_kick->'attackers_far_post'),
            ('attackers_in_6yd_box_at_start', sp.corner_kick->'attackers_in_6yd_box_at_start'),
            ('attackers_in_box', sp.corner_kick->'attackers_in_box'),
            ('attackers_in_box_at_start', sp.corner_kick->'attackers_in_box_at_start'),
            ('attackers_in_central_box', sp.corner_kick->'attackers_in_central_box'),
            ('attackers_near_post', sp.corner_kick->'attackers_near_post'),
            ('defenders_at_first_contact', sp.corner_kick->'defenders_at_first_contact'),
            ('opponent_players_on_pitch', sp.corner_kick->'opponent_players_on_pitch'),
            ('rest_defenders', sp.corner_kick->'rest_defenders'),
            ('short_connectors', sp.corner_kick->'short_connectors'),
            ('team_players_on_pitch', sp.corner_kick->'team_players_on_pitch')
    ) AS roles(role, actor_list)
    CROSS JOIN LATERAL jsonb_array_elements_text(
        CASE
            WHEN jsonb_typeof(roles.actor_list) = 'array' THEN roles.actor_list
            ELSE '[]'::jsonb
        END
    ) AS actor(actor_id)
    WHERE lower(trim(replace(sp.gata_display_name, '-', ' '))) = 'corner kick'
),
array_counts AS (
    SELECT
        corner_id,
        count(DISTINCT actor_id) FILTER (WHERE role = 'attackers_at_first_contact') AS attackers_at_first_contact_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'attackers_edge_of_the_box') AS attackers_edge_of_the_box_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'attackers_far_post') AS attackers_far_post_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'attackers_in_6yd_box_at_start') AS attackers_in_6yd_box_at_start_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'attackers_in_box') AS attackers_in_box_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'attackers_in_box_at_start') AS attackers_in_box_at_start_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'attackers_in_central_box') AS attackers_in_central_box_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'attackers_near_post') AS attackers_near_post_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'defenders_at_first_contact') AS defenders_at_first_contact_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'opponent_players_on_pitch') AS opponent_players_on_pitch_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'rest_defenders') AS rest_defenders_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'short_connectors') AS short_connectors_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'team_players_on_pitch') AS team_players_on_pitch_count
    FROM array_roles
    GROUP BY corner_id
)
SELECT
    c.*,
    CASE WHEN sp.actors->>'taker' IS NOT NULL THEN 1::bigint ELSE 0::bigint END AS taker_count,
    CASE WHEN sp.actors->>'goalkeeper' IS NOT NULL THEN 1::bigint ELSE 0::bigint END AS goalkeeper_count,
    CASE WHEN sp.actors->>'first_contact_player' IS NOT NULL THEN 1::bigint ELSE 0::bigint END AS first_contact_player_count,
    CASE WHEN sp.corner_kick->>'second_contact_player' IS NOT NULL THEN 1::bigint ELSE 0::bigint END AS second_contact_player_count,
    COALESCE(r.attackers_at_first_contact_count, 0) AS attackers_at_first_contact_count,
    COALESCE(r.attackers_edge_of_the_box_count, 0) AS attackers_edge_of_the_box_count,
    COALESCE(r.attackers_far_post_count, 0) AS attackers_far_post_count,
    COALESCE(r.attackers_in_6yd_box_at_start_count, 0) AS attackers_in_6yd_box_at_start_count,
    COALESCE(r.attackers_in_box_count, 0) AS attackers_in_box_count,
    COALESCE(r.attackers_in_box_at_start_count, 0) AS attackers_in_box_at_start_count,
    COALESCE(r.attackers_in_central_box_count, 0) AS attackers_in_central_box_count,
    COALESCE(r.attackers_near_post_count, 0) AS attackers_near_post_count,
    COALESCE(r.defenders_at_first_contact_count, 0) AS defenders_at_first_contact_count,
    COALESCE(r.opponent_players_on_pitch_count, 0) AS opponent_players_on_pitch_count,
    COALESCE(r.rest_defenders_count, 0) AS rest_defenders_count,
    COALESCE(r.short_connectors_count, 0) AS short_connectors_count,
    COALESCE(r.team_players_on_pitch_count, 0) AS team_players_on_pitch_count
FROM v_corners AS c
JOIN setpieces AS sp
    ON sp.id = c.corner_id
LEFT JOIN array_counts AS r
    ON r.corner_id = c.corner_id;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
