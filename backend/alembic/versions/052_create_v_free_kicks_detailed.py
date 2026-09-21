"""Create detailed view for FREE KICK setpieces with all JSONB fields expanded

Revision ID: 052
Revises: 051
Create Date: 2026-09-15 10:30:00.000000

Purpose:
    - Create v_free_kicks_detailed view that expands ALL JSONB fields
    - Extract nested data from entity, time, spatial, actors, phase, channel, free_kick
    - Provide fully denormalized view for analysis and API consumption
    - Make it easy to query free-kick data without complex JSONB traversal

Structure:
    Core fields: setpiece_id, game_id, game_name, period_id, gata_display_name
    
    Entity (extracted):
        - entity_type, entity_name, entity_id
    
    Time (extracted):
        - start_seconds, end_seconds, duration_seconds, start_frame, end_frame
        - quick_restart, time_to_restart
    
    Spatial (extracted):
        - angle, direction, side, corridor, distance_meters, height
        - start_location_x, start_location_y, end_location_x, end_location_y
    
    Actors (extracted):
        - player_id, player_name, team_id, team_brand
        - opponent_team_id, opponent_team_brand
        - targeted_player_id, targeted_player_name
        - goalkeeper_id, goalkeeper_name
        - first_contact_player_id, first_contact_player_name
        - players_to_bypass (array as text)
    
    Phase (extracted):
        - possession_id, type_of_play_id, phase_of_play_id
        - individual_possession_id, next_individual_possession_id
    
    Channel (extracted):
        - start_channel, end_channel
    
    Free-Kick Specific:
        - free_kick_link, free_kick_meta (all nested fields)
        - free_kick_type (if available)
    
    Audit:
        - created_at, updated_at
    
    Raw JSONB (reference):
        - full_entity, full_time, full_spatial, full_actors, full_phase, full_channel, full_free_kick
"""

from alembic import op
import sqlalchemy as sa


revision = '052'
down_revision = '051'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create v_free_kicks_detailed view"""
    
    op.execute("""
    DROP VIEW IF EXISTS v_free_kicks_detailed CASCADE
    """)
    
    op.execute("""
    CREATE VIEW v_free_kicks_detailed AS
    SELECT 
        -- ====================================================================
        -- CORE IDENTIFIERS & GAME INFO
        -- ====================================================================
        sp.id as setpiece_id,
        sp.game_id,
        g.name as game_name,
        g.starts_at::date as game_date,
        g.round as game_round,
        g.round_name as game_round_name,
        
        -- ====================================================================
        -- PERIOD & TIMING (from time JSONB)
        -- ====================================================================
        sp.period_id,
        (sp.time->>'start')::numeric as time_start_seconds,
        (sp.time->>'end')::numeric as time_end_seconds,
        (sp.time->>'duration')::numeric as time_duration_seconds,
        (sp.time->>'start_frame')::integer as time_start_frame,
        (sp.time->>'end_frame')::integer as time_end_frame,
        (sp.time->>'quick_restart')::boolean as time_quick_restart,
        (sp.time->>'time_to_restart')::numeric as time_to_restart_seconds,
        
        -- ====================================================================
        -- ENTITY INFO (from entity JSONB)
        -- ====================================================================
        (sp.entity->>'type')::text as entity_type,
        (sp.entity->>'name')::text as entity_name,
        (sp.entity->>'id')::text as entity_id,
        sp.gata_display_name as entity_gata_display_name,
        
        -- ====================================================================
        -- SPATIAL DATA (from spatial JSONB)
        -- ====================================================================
        (sp.spatial->>'angle')::numeric as spatial_angle,
        (sp.spatial->>'direction')::text as spatial_direction,
        (sp.spatial->>'side')::text as spatial_side,
        (sp.spatial->>'corridor')::text as spatial_corridor,
        (sp.spatial->>'distance')::numeric as spatial_distance_meters,
        (sp.spatial->>'distance_gained')::numeric as spatial_distance_gained,
        (sp.spatial->>'height')::text as spatial_height,
        -- Start Location (nested object)
        (sp.spatial->'start_location'->>'x')::numeric as spatial_start_location_x,
        (sp.spatial->'start_location'->>'y')::numeric as spatial_start_location_y,
        (sp.spatial->'start_location'->>'z')::numeric as spatial_start_location_z,
        -- End Location (nested object)
        (sp.spatial->'end_location'->>'x')::numeric as spatial_end_location_x,
        (sp.spatial->'end_location'->>'y')::numeric as spatial_end_location_y,
        (sp.spatial->'end_location'->>'z')::numeric as spatial_end_location_z,
        
        -- ====================================================================
        -- ACTORS (from actors JSONB)
        -- ====================================================================
        sp.player_id,
        p.name as player_name,
        p.positions::text as player_position,
        sp.team_id,
        t.name as team_name,
        t.brand as team_brand,
        sp.opponent_team_id,
        ot.name as opponent_team_name,
        ot.brand as opponent_team_brand,
        -- Targeted Player
        (sp.actors->>'targeted_player')::text as targeted_player_id,
        (SELECT name FROM players WHERE id::text = (sp.actors->>'targeted_player') LIMIT 1) as targeted_player_name,
        -- Goalkeeper
        (sp.actors->>'goalkeeper')::text as goalkeeper_id,
        (SELECT name FROM players WHERE id::text = (sp.actors->>'goalkeeper') LIMIT 1) as goalkeeper_name,
        -- First Contact Player
        (sp.actors->>'first_contact_player')::text as first_contact_player_id,
        (SELECT name FROM players WHERE id::text = (sp.actors->>'first_contact_player') LIMIT 1) as first_contact_player_name,
        -- Players to Bypass (array as text)
        sp.actors->'players_to_bypass'::text as actors_players_to_bypass_json,
        
        -- ====================================================================
        -- PHASE (from phase JSONB)
        -- ====================================================================
        (sp.phase->>'possession')::text as phase_possession_id,
        (sp.phase->>'type_of_play')::text as phase_type_of_play_id,
        (sp.phase->>'phase_of_play')::text as phase_phase_of_play_id,
        (sp.phase->>'individual_possession')::text as phase_individual_possession_id,
        (sp.phase->>'next_individual_possession')::text as phase_next_individual_possession_id,
        
        -- ====================================================================
        -- CHANNEL (from channel JSONB)
        -- ====================================================================
        (sp.channel->>'start_channel')::text as channel_start,
        (sp.channel->>'end_channel')::text as channel_end,
        
        -- ====================================================================
        -- FREE-KICK SPECIFIC DATA (from free_kick JSONB - only for FREE KICK type)
        -- ====================================================================
        sp.free_kick->>'link' as free_kick_link,
        sp.free_kick->>'type' as free_kick_type,
        sp.free_kick->>'meta' as free_kick_meta_json,
        
        -- ====================================================================
        -- AUDIT TIMESTAMPS
        -- ====================================================================
        sp.created_at,
        sp.updated_at,
        
        -- ====================================================================
        -- RAW JSONB FOR REFERENCE (for developers)
        -- ====================================================================
        sp.entity as full_entity_jsonb,
        sp.time as full_time_jsonb,
        sp.spatial as full_spatial_jsonb,
        sp.actors as full_actors_jsonb,
        sp.phase as full_phase_jsonb,
        sp.channel as full_channel_jsonb,
        sp.free_kick as full_free_kick_jsonb
        
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.team_id::text = t.id::text
    LEFT JOIN teams ot ON sp.opponent_team_id::text = ot.id::text
    LEFT JOIN players p ON sp.player_id::text = p.id::text
    
    WHERE 
        sp.gata_display_name = 'Free-kick'
        OR sp.gata_display_name = 'Direct free-kick'
    
    ORDER BY 
        g.starts_at DESC, 
        sp.period_id DESC, 
        (sp.time->>'start')::numeric DESC
    """)


def downgrade() -> None:
    """Drop v_free_kicks_detailed view"""
    op.execute("DROP VIEW IF EXISTS v_free_kicks_detailed CASCADE")
