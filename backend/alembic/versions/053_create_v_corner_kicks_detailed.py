"""Create detailed views for all CORNER KICK setpieces with all JSONB fields expanded

Revision ID: 053
Revises: 052
Create Date: 2026-09-15 10:35:00.000000

Purpose:
    - Create v_corner_kicks_detailed view (expands ALL JSONB fields)
    - Extract nested data specific to corner kicks
    - Include corner-specific data (attackers, defenders, outcome, etc.)
"""

from alembic import op


revision = '053'
down_revision = '052'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create v_corner_kicks_detailed view"""
    
    op.execute("""
    DROP VIEW IF EXISTS v_corner_kicks_detailed CASCADE
    """)
    
    op.execute("""
    CREATE VIEW v_corner_kicks_detailed AS
    SELECT 
        -- Core
        sp.id as setpiece_id,
        sp.game_id,
        g.name as game_name,
        g.starts_at::date as game_date,
        g.round as game_round,
        
        -- Period & Timing
        sp.period_id,
        (sp.time->>'start')::numeric as time_start_seconds,
        (sp.time->>'end')::numeric as time_end_seconds,
        (sp.time->>'duration')::numeric as time_duration_seconds,
        (sp.time->>'start_frame')::integer as time_start_frame,
        (sp.time->>'end_frame')::integer as time_end_frame,
        (sp.time->>'quick_restart')::boolean as time_quick_restart,
        
        -- Entity
        (sp.entity->>'type')::text as entity_type,
        sp.gata_display_name,
        
        -- Spatial
        (sp.spatial->>'angle')::numeric as spatial_angle,
        (sp.spatial->>'direction')::text as spatial_direction,
        (sp.spatial->>'side')::text as spatial_side,
        (sp.spatial->>'distance')::numeric as spatial_distance_meters,
        (sp.spatial->>'height')::text as spatial_height,
        (sp.spatial->'start_location'->>'x')::numeric as start_location_x,
        (sp.spatial->'start_location'->>'y')::numeric as start_location_y,
        (sp.spatial->'end_location'->>'x')::numeric as end_location_x,
        (sp.spatial->'end_location'->>'y')::numeric as end_location_y,
        
        -- Actors
        sp.player_id,
        p.name as player_name,
        sp.team_id,
        t.name as team_name,
        t.brand as team_brand,
        sp.opponent_team_id,
        ot.name as opponent_team_name,
        ot.brand as opponent_team_brand,
        (sp.actors->>'targeted_player')::text as targeted_player_id,
        (sp.actors->>'goalkeeper')::text as goalkeeper_id,
        (sp.actors->>'first_contact_player')::text as first_contact_player_id,
        
        -- Phase
        (sp.phase->>'possession')::text as phase_possession_id,
        (sp.phase->>'type_of_play')::text as phase_type_of_play_id,
        (sp.phase->>'phase_of_play')::text as phase_phase_of_play_id,
        
        -- Channel
        (sp.channel->>'start_channel')::text as channel_start,
        (sp.channel->>'end_channel')::text as channel_end,
        
        -- CORNER-SPECIFIC DATA
        (sp.corner_kick->>'type')::text as corner_type,
        (sp.corner_kick->>'outcome')::text as corner_outcome,
        (sp.corner_kick->>'short')::boolean as corner_is_short,
        (sp.corner_kick->>'goalkeeper')::boolean as corner_involved_goalkeeper,
        sp.corner_kick->'attackers' as corner_attackers_json,
        sp.corner_kick->'defenders' as corner_defenders_json,
        sp.corner_kick->'meta' as corner_meta_json,
        
        -- Audit
        sp.created_at,
        sp.updated_at,
        
        -- Raw JSONB
        sp.corner_kick as full_corner_kick_jsonb
        
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.team_id::text = t.id::text
    LEFT JOIN teams ot ON sp.opponent_team_id::text = ot.id::text
    LEFT JOIN players p ON sp.player_id::text = p.id::text
    
    WHERE sp.gata_display_name = 'Corner kick'
    
    ORDER BY g.starts_at DESC, sp.period_id DESC, (sp.time->>'start')::numeric DESC
    """)


def downgrade() -> None:
    """Drop v_corner_kicks_detailed view"""
    op.execute("DROP VIEW IF EXISTS v_corner_kicks_detailed CASCADE")
