-- ============================================================================
-- DATABASE VIEWS: Distance Analytics
-- ============================================================================
-- Created: 2026-08-18
-- Purpose: Queryable views for distance and performance metrics analysis
-- ============================================================================

-- Drop existing views (needed when changing SELECT structure)
DROP VIEW IF EXISTS v_player_distance_by_speed_zone CASCADE;
DROP VIEW IF EXISTS v_player_distance_by_zone_interval CASCADE;
DROP VIEW IF EXISTS v_periods CASCADE;
DROP VIEW IF EXISTS v_player_speed_zones_by_interval CASCADE;
DROP VIEW IF EXISTS v_team_speed_zones_by_interval CASCADE;
DROP VIEW IF EXISTS v_team_matches_summary CASCADE;
DROP VIEW IF EXISTS v_goals CASCADE;
DROP VIEW IF EXISTS v_corner_strategy CASCADE;
DROP VIEW IF EXISTS v_corner_actors CASCADE;
DROP VIEW IF EXISTS v_corners CASCADE;

-- ============================================================================
-- VIEW: Corner kicks with game, team, taker, and outcome context
-- ============================================================================
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
WHERE lower(trim(replace(sp.gata_display_name, '-', ' '))) = 'corner kick';

-- ============================================================================
-- VIEW: Player actors and roles for each corner
-- ============================================================================
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
    WHERE corner_kick->>'offensive_first_contact' = 'true'
    UNION ALL
    SELECT corner_id, 'second_contact_player', corner_kick->>'second_contact_player'
    FROM corner_setpieces
    WHERE corner_kick->>'offensive_second_contact' = 'true'
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
    actor_roles.role,
    c.side,
    lineup_player.shirt_number
FROM actor_roles
JOIN v_corners AS c
    ON c.corner_id = actor_roles.corner_id
LEFT JOIN players AS player
    ON player.id = actor_roles.actor_id
LEFT JOIN LATERAL (
    SELECT lineup_player.shirt_number
    FROM lineup_players AS lineup_player
    JOIN lineup_teams AS lineup_team
        ON lineup_team.id = lineup_player.lineup_team_id
    WHERE lineup_player.player_id = actor_roles.actor_id
      AND lineup_team.game_id = c.game_id
      AND lineup_team.team_id IN (c.team_id, c.opponent_team_id)
) AS lineup_player ON TRUE;

-- ============================================================================
-- VIEW: Per-corner counts of distinct players in each tactical role
-- ============================================================================
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
    ON r.corner_id = c.corner_id;

-- ============================================================================
-- VIEW: Canonical goals with team, round, and tactical context
-- ============================================================================
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
   AND shot_event.entity->>'sequence_id' = go.shot #>> '{}';

-- ============================================================================
-- VIEW 1: Periods with Orientation Coefficients
-- ============================================================================
-- Shows each period with team orientation coefficient (direction)
CREATE OR REPLACE VIEW v_periods AS
WITH period_teams AS (
    -- Extract HOME team (index 0)
    SELECT 
        p.id as period_id,
        p.game_id as game_id,
        p.period_id as period,
        g.name as game,
        (p.direction->0->>'team_id') as team_id,
        ht.name as team,
        (p.direction->0->>'value') as value,
        (p.direction->0->>'coef')::INTEGER as coef
    FROM periods p
    JOIN games g ON p.game_id = g.id
    JOIN teams ht ON (p.direction->0->>'team_id') = ht.id
    WHERE p.direction IS NOT NULL
    UNION ALL
    -- Extract AWAY team (index 1)
    SELECT 
        p.id,
        p.game_id,
        p.period_id,
        g.name,
        (p.direction->1->>'team_id'),
        at.name,
        (p.direction->1->>'value'),
        (p.direction->1->>'coef')::INTEGER
    FROM periods p
    JOIN games g ON p.game_id = g.id
    JOIN teams at ON (p.direction->1->>'team_id') = at.id
    WHERE p.direction IS NOT NULL
)
SELECT 
    period_id,
    game_id,
    period,
    game,
    team_id,
    team,
    value,
    coef
FROM period_teams
ORDER BY game_id, period, team_id;

-- ============================================================================
-- VIEW 2: Player Distance by Speed Zone (Aggregated)
-- ============================================================================
-- Shows player distance metrics aggregated by speed zone (no time intervals)
CREATE OR REPLACE VIEW v_player_distance_by_speed_zone AS
WITH speed_zone_breakdown AS (
    -- Unpivot speed zones into rows
    SELECT 
        pdc.game_id,
        pdc.player_id,
        pdc.team_id,
        'walking' as speed_zone,
        (pdc.speed_zones->>'walking')::FLOAT as distance_m
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'walking' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, pdc.team_id, 'jogging', 
        (pdc.speed_zones->>'jogging')::FLOAT
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'jogging' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, pdc.team_id, 'moderated_intensity', 
        (pdc.speed_zones->>'moderated_intensity')::FLOAT
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'moderated_intensity' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, pdc.team_id, 'high_intensity', 
        (pdc.speed_zones->>'high_intensity')::FLOAT
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'high_intensity' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, pdc.team_id, 'sprint', 
        (pdc.speed_zones->>'sprint')::FLOAT
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'sprint' IS NOT NULL
)
SELECT 
    g.name as game_name,
    p.name as player_name,
    t.name as team_name,
    szb.speed_zone,
    szb.distance_m,
    ROUND((pdc.metrics->>'total_distance_m')::NUMERIC, 2) as total_distance_m,
    ROUND((pdc.metrics->>'distance_per_min_played_m')::NUMERIC, 2) as distance_per_min_played_m,
    ROUND((pdc.metrics->>'minutes_played')::NUMERIC, 2) as minutes_played
FROM player_distance_covered pdc
JOIN games g ON pdc.game_id = g.id
JOIN players p ON pdc.player_id = p.id
JOIN teams t ON pdc.team_id = t.id
JOIN speed_zone_breakdown szb ON pdc.game_id = szb.game_id AND pdc.player_id = szb.player_id
ORDER BY g.name, p.name, szb.speed_zone;

-- ============================================================================
-- VIEW 3: Player Distance by Speed Zone and Time Interval
-- ============================================================================
-- Shows player distance metrics broken down by speed zone and time interval
CREATE OR REPLACE VIEW v_player_distance_by_zone_interval AS
WITH speed_zone_breakdown AS (
    -- Unpivot speed zones into rows
    SELECT 
        pdc.game_id,
        pdc.player_id,
        pdc.team_id,
        'walking' as speed_zone,
        (pdc.speed_zones->>'walking')::FLOAT as distance_m
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'walking' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, pdc.team_id, 'jogging', 
        (pdc.speed_zones->>'jogging')::FLOAT
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'jogging' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, pdc.team_id, 'moderated_intensity', 
        (pdc.speed_zones->>'moderated_intensity')::FLOAT
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'moderated_intensity' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, pdc.team_id, 'high_intensity', 
        (pdc.speed_zones->>'high_intensity')::FLOAT
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'high_intensity' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, pdc.team_id, 'sprint', 
        (pdc.speed_zones->>'sprint')::FLOAT
    FROM player_distance_covered pdc
    WHERE pdc.speed_zones->>'sprint' IS NOT NULL
),
time_interval_breakdown AS (
    -- Unpivot time intervals into rows
    SELECT pdc.game_id, pdc.player_id, '0_5' as time_interval, (pdc.time_intervals->>'0_5')::FLOAT as interval_distance_m
    FROM player_distance_covered pdc WHERE pdc.time_intervals->>'0_5' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '5_10', (pdc.time_intervals->>'5_10')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'5_10' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '10_15', (pdc.time_intervals->>'10_15')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'10_15' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '15_20', (pdc.time_intervals->>'15_20')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'15_20' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '20_25', (pdc.time_intervals->>'20_25')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'20_25' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '25_30', (pdc.time_intervals->>'25_30')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'25_30' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '30_35', (pdc.time_intervals->>'30_35')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'30_35' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '35_40', (pdc.time_intervals->>'35_40')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'35_40' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '40_45', (pdc.time_intervals->>'40_45')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'40_45' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '45_50', (pdc.time_intervals->>'45_50')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'45_50' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '50_55', (pdc.time_intervals->>'50_55')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'50_55' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '55_60', (pdc.time_intervals->>'55_60')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'55_60' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '60_65', (pdc.time_intervals->>'60_65')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'60_65' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '65_70', (pdc.time_intervals->>'65_70')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'65_70' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '70_75', (pdc.time_intervals->>'70_75')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'70_75' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '75_80', (pdc.time_intervals->>'75_80')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'75_80' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '80_85', (pdc.time_intervals->>'80_85')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'80_85' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '85_90', (pdc.time_intervals->>'85_90')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'85_90' IS NOT NULL
    UNION ALL
    SELECT pdc.game_id, pdc.player_id, '90+', (pdc.time_intervals->>'90+')::FLOAT FROM player_distance_covered pdc WHERE pdc.time_intervals->>'90+' IS NOT NULL
)
SELECT 
    ROUND((pdc.metrics->>'total_distance_m')::NUMERIC, 2) as total_distance_m,
    szb.speed_zone,
    tib.time_interval,
    p.name as player_name,
    g.name as game_name,
    t.name as team_name
FROM player_distance_covered pdc
JOIN games g ON pdc.game_id = g.id
JOIN players p ON pdc.player_id = p.id
JOIN teams t ON pdc.team_id = t.id
LEFT JOIN speed_zone_breakdown szb ON pdc.game_id = szb.game_id AND pdc.player_id = szb.player_id
LEFT JOIN time_interval_breakdown tib ON pdc.game_id = tib.game_id AND pdc.player_id = tib.player_id
ORDER BY g.name, p.name, tib.time_interval, szb.speed_zone;

-- ============================================================================
-- VIEW SUMMARY
-- ============================================================================
-- v_periods: Periods with team orientation coefficient
-- v_player_distance_by_zone_interval: Player distance metrics by speed zone and time interval
-- v_team_speed_zones_by_interval: Speed zones × Time intervals for teams
-- v_player_speed_zones_by_interval: Speed zones × Time intervals for players
-- v_team_matches_summary: Match results, scores, goals, cards, substitutions per team
-- ============================================================================
