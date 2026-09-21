"""Create detailed setpieces view

Revision ID: 045_create_v_setpieces_detailed
Revises: 044_add_logo_url_to_teams
Create Date: 2026-09-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '045_create_v_setpieces_detailed'
down_revision = '044_add_logo_url_to_teams'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing view if it exists
    op.execute("DROP VIEW IF EXISTS v_setpieces_detailed CASCADE")
    
    # Create detailed setpieces view with CORRECT JSON structure
    # JSON structure: entity{type, gata_display_name}, time{start, end, duration, start_frame, end_frame}
    #                 spatial{distance, distance_gained}, actors{team, opponent_team, player_in_possession}
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
    # Drop the view
    op.execute("DROP VIEW IF EXISTS v_setpieces_detailed")
