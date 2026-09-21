"""Create summary view for team distance covered - metrics and speed zones only

Revision ID: 059_create_v_team_distance_summary
Revises: 058
Create Date: 2026-09-15 11:05:00.000000

Purpose:
    - Create v_team_distance_summary view
    - Extract ONLY metrics and speed_zones JSONB fields
    - Simple, focused view for team distance analysis
    - Fully denormalized: no JSON traversal needed
    
Structure:
    Core: game_id, game_name, round, team_id, team_name
    
    Metrics (from metrics JSONB):
        - total_distance_m
    
    Speed Zones (from speed_zones JSONB):
        - walking_m
        - jogging_m
        - moderated_intensity_m
        - high_intensity_m
        - sprint_m
    
    Calculated Fields:
        - high_intensity_distance (high_intensity_m + sprint_m)
        - low_intensity_distance (walking_m + jogging_m)
        - intensity_ratio (high intensity / total distance %)
"""

from alembic import op


revision = '059_create_v_team_distance_summary'
down_revision = '058'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create v_team_distance_summary view"""
    
    op.execute("""
    DROP VIEW IF EXISTS v_team_distance_summary CASCADE
    """)
    
    op.execute("""
    CREATE VIEW v_team_distance_summary AS
    SELECT 
        -- ====================================================================
        -- CORE IDENTIFIERS & GAME INFO
        -- ====================================================================
        tdc.game_id,
        g.name as game_name,
        g.starts_at::date as game_date,
        g.round as game_round,
        g.round_name as game_round_name,
        g.result as game_result,
        
        -- ====================================================================
        -- TEAM INFO
        -- ====================================================================
        tdc.team_id,
        t.name as team_name,
        t.brand as team_brand,
        
        -- Identify if home or away
        CASE 
            WHEN tdc.team_id::text = g.home_team_id::text THEN 'HOME'
            WHEN tdc.team_id::text = g.away_team_id::text THEN 'AWAY'
            ELSE 'UNKNOWN'
        END as team_side,
        
        -- ====================================================================
        -- METRICS (from metrics JSONB)
        -- ====================================================================
        (tdc.metrics->>'total_distance_m')::numeric as total_distance_m,
        (tdc.metrics->>'minutes_played')::numeric as minutes_played,
        
        -- ====================================================================
        -- SPEED ZONES (from speed_zones JSONB)
        -- ====================================================================

        (tdc.speed_zones->>'walking')::numeric as walking_m,
        (tdc.speed_zones->>'jogging')::numeric as jogging_m,
        (tdc.speed_zones->>'moderated_intensity')::numeric as moderated_intensity_m,
        (tdc.speed_zones->>'high_intensity')::numeric as high_intensity_m,
        (tdc.speed_zones->>'sprint')::numeric as sprint_m,
        
        -- ====================================================================
        -- CALCULATED FIELDS
        -- ====================================================================
        -- High intensity distance (high_intensity + sprint)
        (
            (tdc.speed_zones->>'high_intensity')::numeric +
            (tdc.speed_zones->>'sprint')::numeric
        )::numeric as high_intensity_distance_m,
        
        -- Low intensity distance (walking + jogging)
        (
            (tdc.speed_zones->>'walking')::numeric +
            (tdc.speed_zones->>'jogging')::numeric
        )::numeric as low_intensity_distance_m,
        
        -- Intensity ratio: high intensity / total distance (%)
        CASE 
            WHEN (tdc.metrics->>'total_distance_m')::numeric > 0
            THEN ROUND(
                (
                    (
                        (tdc.speed_zones->>'high_intensity')::numeric +
                        (tdc.speed_zones->>'sprint')::numeric
                    ) / 
                    (tdc.metrics->>'total_distance_m')::numeric * 100
                )::numeric, 2
            )
            ELSE NULL
        END as high_intensity_ratio_percent,
        
        -- Average speed (total_distance / 90 minutes typical)
        ROUND(
            ((tdc.metrics->>'total_distance_m')::numeric / 90)::numeric, 2
        ) as avg_speed_m_per_minute,
        
        -- ====================================================================
        -- AUDIT TIMESTAMPS
        -- ====================================================================
        tdc.created_at,
        tdc.updated_at,
        
        -- ====================================================================
        -- RAW JSONB FOR REFERENCE
        -- ====================================================================
        tdc.metrics as full_metrics_jsonb,
        tdc.speed_zones as full_speed_zones_jsonb,
        tdc.game_state as full_game_state_jsonb,
        tdc.time_intervals as full_time_intervals_jsonb
        
    FROM team_distance_covered tdc
    LEFT JOIN games g ON tdc.game_id::text = g.id::text
    LEFT JOIN teams t ON tdc.team_id::text = t.id::text
    
    ORDER BY 
        g.starts_at DESC, 
        t.name ASC
    """)


def downgrade() -> None:
    """Drop v_team_distance_summary view"""
    op.execute("DROP VIEW IF EXISTS v_team_distance_summary CASCADE")
