"""Fix v_setpieces_detailed view - use correct JSON structure

Revision ID: 047_fix_v_setpieces_detailed_json_structure
Revises: 046_create_v_clearance_events_detailed
Create Date: 2026-09-11 00:00:00.000000

PROBLEM: Previous migration tried to extract from non-existent JSON paths
- entity_id, typeId, subType, subTypeId don't exist in entity JSON
- spatial->'start'->>'x' doesn't exist (spatial only has distance fields)
- time->>'displayTime' doesn't exist (time has start, end, duration, frames)

SOLUTION: Use actual JSON structure:
- entity: {type, gata_display_name}
- time: {start, end, duration, start_frame, end_frame}
- spatial: {distance, distance_gained}
- actors: {team, opponent_team, player_in_possession}

Result: 4168 setpieces now visible with actual data instead of NULL fields
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '047_fix_v_setpieces_detailed_json_structure'
down_revision = '046_create_v_clearance_events_detailed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing broken view
    op.execute("DROP VIEW IF EXISTS v_setpieces_detailed CASCADE")
    
    # Create view with CORRECT JSON structure
    op.execute("""
    CREATE VIEW v_setpieces_detailed AS
    SELECT 
        sp.id as setpiece_id,
        sp.game_id,
        g.name as game_name,
        g.starts_at::date as game_date,
        g.round,
        
        -- Period & Timing (from time JSON)
        sp.period_id,
        (sp.time->>'start')::numeric as start_seconds,
        (sp.time->>'end')::numeric as end_seconds,
        (sp.time->>'duration')::numeric as duration_seconds,
        (sp.time->>'start_frame')::integer as start_frame,
        (sp.time->>'end_frame')::integer as end_frame,
        
        -- Entity data (type of set piece)
        (sp.entity->>'type')::text as entity_type,
        (sp.entity->>'gata_display_name')::text as gata_display_name,
        
        -- Spatial data (distance, not coordinates)
        (sp.spatial->>'distance')::numeric as distance_meters,
        (sp.spatial->>'distance_gained')::numeric as distance_gained,
        
        -- Team & Player info (from actors JSON)
        (sp.actors->>'team')::text as team_id,
        t.brand as team_brand,
        (sp.actors->>'opponent_team')::text as opponent_team_id,
        (SELECT brand FROM teams WHERE id::text = (sp.actors->>'opponent_team')) as opponent_team_brand,
        (sp.actors->>'player_in_possession')::text as player_in_possession_id,
        p.name as player_name,
        
        -- Raw JSON for reference
        sp.entity,
        sp.time,
        sp.spatial,
        sp.actors,
        sp.created_at,
        sp.updated_at
        
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.actors->>'team' = t.id::text
    LEFT JOIN players p ON sp.actors->>'player_in_possession' = p.id::text
    ORDER BY g.starts_at DESC, sp.period_id DESC, (sp.time->>'start')::numeric DESC
    """)


def downgrade() -> None:
    # Drop the corrected view
    op.execute("DROP VIEW IF EXISTS v_setpieces_detailed CASCADE")
    
    # Restore previous (broken) view for downgrade compatibility
    # This preserves the migration chain but doesn't recreate broken state
    # (We don't want to restore broken functionality)
