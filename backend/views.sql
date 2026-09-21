-- ============================================================================
-- DATABASE VIEWS: Distance Analytics
-- ============================================================================
-- Created: 2026-08-18
-- Purpose: Queryable views for distance and performance metrics analysis
-- ============================================================================

-- Drop existing views (needed when changing SELECT structure)
DROP VIEW IF EXISTS v_player_distance_summary CASCADE;
DROP VIEW IF EXISTS v_player_distance_by_speed_zone CASCADE;
DROP VIEW IF EXISTS v_player_distance_by_zone_interval CASCADE;
DROP VIEW IF EXISTS v_periods CASCADE;
DROP VIEW IF EXISTS v_player_speed_zones_by_interval CASCADE;
DROP VIEW IF EXISTS v_team_speed_zones_by_interval CASCADE;
DROP VIEW IF EXISTS v_team_matches_summary CASCADE;

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
-- VIEW 2b: Player Distance Summary (total distance + minutes played only)
-- ============================================================================
-- Minimal per-player, per-game summary: just total distance and minutes played
CREATE OR REPLACE VIEW v_player_distance_summary AS
SELECT
    pdc.game_id,
    pdc.player_id,
    pdc.team_id,
    g.name as game_name,
    p.name as player_name,
    t.name as team_name,
    ROUND((pdc.metrics->>'total_distance_m')::NUMERIC, 2) as total_distance_m,
    ROUND((pdc.metrics->>'minutes_played')::NUMERIC, 2) as minutes_played
FROM player_distance_covered pdc
LEFT JOIN games g ON pdc.game_id = g.id
LEFT JOIN players p ON pdc.player_id = p.id
LEFT JOIN teams t ON pdc.team_id = t.id
ORDER BY g.name, p.name;

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
-- v_player_distance_summary: Total distance and minutes played per player/game
-- v_player_distance_by_zone_interval: Player distance metrics by speed zone and time interval
-- v_team_speed_zones_by_interval: Speed zones × Time intervals for teams
-- v_player_speed_zones_by_interval: Speed zones × Time intervals for players
-- v_team_matches_summary: Match results, scores, goals, cards, substitutions per team
-- ============================================================================
