"""Create summary view for player distance covered - metrics and speed zones only

Revision ID: 058
Revises: 057
Create Date: 2026-09-15 11:00:00.000000

Purpose:
    - Create v_player_distance_summary view with simplified columns
    - Extract only metrics and speed_zones JSONB fields (no game_state, no time_intervals)
    - Join with games, players, and teams for denormalized data
    - Add calculated fields: high_intensity_distance_m, intensity ratio, per-minute distance

Structure:
    Core Fields: game_id, player_id, game_name, player_name, player_position
    Team: team_id, team_name, team_brand
    Metrics: total_distance_m (from metrics->>'total_distance_m')
    Speed Zones: walking_m, jogging_m, moderated_intensity_m, high_intensity_m, sprint_m
    Calculated: high_intensity_distance_m, low_intensity_distance_m, distance_per_minute_m
    Audit: created_at, updated_at
    Raw JSONB: full_metrics_jsonb, full_speed_zones_jsonb (for reference)
"""

from alembic import op


revision = '058'
down_revision = '057'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create v_player_distance_summary view"""
    
    op.execute("""
    DROP VIEW IF EXISTS v_player_distance_summary CASCADE
    """)
    
    op.execute("""
    CREATE VIEW v_player_distance_summary AS
    SELECT 
        -- ====================================================================
        -- CORE IDENTIFIERS & GAME INFO
        -- ====================================================================
        pdc.game_id,
        g.name as game_name,
        g.starts_at::date as game_date,
        g.round as game_round,
        
        -- ====================================================================
        -- PLAYER INFO
        -- ====================================================================
        pdc.player_id,
        p.name as player_name,
        p.usage_name as player_usage_name,
        p.positions::text as player_position,
        p.age as player_age,
        
        -- ====================================================================
        -- TEAM INFO (from player_distance_covered.team_id)
        -- ====================================================================
        pdc.team_id,
        t.name as team_name,
        t.brand as team_brand,
        
        -- ====================================================================
        -- METRICS (from metrics JSONB)
        -- ====================================================================
        (pdc.metrics->>'total_distance_m')::numeric as total_distance_m,
        (pdc.metrics->>'minutes_played')::numeric as minutes_played,
        
        -- ====================================================================
        -- SPEED ZONES (from speed_zones JSONB)
        -- ====================================================================

        (pdc.speed_zones->>'walking')::numeric as walking_m,
        (pdc.speed_zones->>'jogging')::numeric as jogging_m,
        (pdc.speed_zones->>'moderated_intensity')::numeric as moderated_intensity_m,
        (pdc.speed_zones->>'high_intensity')::numeric as high_intensity_m,
        (pdc.speed_zones->>'sprint')::numeric as sprint_m,
        
        -- ====================================================================
        -- CALCULATED FIELDS
        -- ====================================================================
        -- High intensity distance (high_intensity + sprint)
        (
            (pdc.speed_zones->>'high_intensity')::numeric +
            (pdc.speed_zones->>'sprint')::numeric
        )::numeric as high_intensity_distance_m,
        
        -- Low intensity distance (walking + jogging)
        (
            (pdc.speed_zones->>'walking')::numeric +
            (pdc.speed_zones->>'jogging')::numeric
        )::numeric as low_intensity_distance_m,
        
        -- Distance per minute (from metrics if available)
        (pdc.metrics->>'distance_per_min_played_m')::numeric as distance_per_minute_m,
        
        -- ====================================================================
        -- AUDIT TIMESTAMPS
        -- ====================================================================
        pdc.created_at,
        pdc.updated_at,
        
        -- ====================================================================
        -- RAW JSONB FOR REFERENCE (for developers)
        -- ====================================================================
        pdc.metrics as full_metrics_jsonb,
        pdc.speed_zones as full_speed_zones_jsonb,
        pdc.game_state as full_game_state_jsonb,
        pdc.time_intervals as full_time_intervals_jsonb
        
    FROM player_distance_covered pdc
    LEFT JOIN games g ON pdc.game_id::text = g.id::text
    LEFT JOIN players p ON pdc.player_id::text = p.id::text
    LEFT JOIN teams t ON pdc.team_id::text = t.id::text
    
    ORDER BY 
        g.starts_at DESC, 
        p.name ASC
    """)


def downgrade() -> None:
    """Drop v_player_distance_summary view"""
    op.execute("DROP VIEW IF EXISTS v_player_distance_summary CASCADE")
