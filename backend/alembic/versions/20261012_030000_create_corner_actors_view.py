"""Create a per-player-role view for corner events.

Revision ID: 20261012_030000
Revises: 20261012_020000
"""

from alembic import op


revision = "20261012_030000"
down_revision = "20261012_020000"
branch_labels = None
depends_on = None


VIEW_SQL = """
CREATE OR REPLACE VIEW v_corner_actors AS
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
    ON player.id = actor_roles.actor_id
"""


def upgrade() -> None:
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_corner_actors")
