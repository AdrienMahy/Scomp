"""Calculate corner role counts directly from stored actor arrays.

Revision ID: 20261012_070000
Revises: 20261012_060000
"""

from alembic import op


revision = "20261012_070000"
down_revision = "20261012_060000"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
CREATE OR REPLACE VIEW v_corner_strategy AS
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
    ON r.corner_id = c.corner_id
"""


DOWNGRADE_SQL = """
CREATE OR REPLACE VIEW v_corner_strategy AS
WITH role_counts AS (
    SELECT
        corner_id,
        count(DISTINCT actor_id) FILTER (WHERE role = 'taker') AS taker_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'goalkeeper') AS goalkeeper_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'first_contact_player') AS first_contact_player_count,
        count(DISTINCT actor_id) FILTER (WHERE role = 'second_contact_player') AS second_contact_player_count,
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
    FROM v_corner_actors
    GROUP BY corner_id
)
SELECT
    c.*,
    COALESCE(r.taker_count, 0) AS taker_count,
    COALESCE(r.goalkeeper_count, 0) AS goalkeeper_count,
    COALESCE(r.first_contact_player_count, 0) AS first_contact_player_count,
    COALESCE(r.second_contact_player_count, 0) AS second_contact_player_count,
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
LEFT JOIN role_counts AS r
    ON r.corner_id = c.corner_id
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
