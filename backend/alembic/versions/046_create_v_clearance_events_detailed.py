"""Create detailed clearance events view

Revision ID: 046_create_v_clearance_events_detailed
Revises: 045_create_v_setpieces_detailed
Create Date: 2026-09-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '046_create_v_clearance_events_detailed'
down_revision = '045_create_v_setpieces_detailed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing view if it exists
    op.execute("DROP VIEW IF EXISTS v_clearance_events_detailed CASCADE")
    
    # Create detailed clearance events view from entity JSON (flat structure)
    # JSON structure for clearance events: flat fields with gata_display_name = "Clearance"
    op.execute("""
    CREATE VIEW v_clearance_events_detailed AS
    SELECT 
        e.id as event_id,
        e.game_id,
        g.name as game_name,
        g.starts_at::date as game_date,
        g.round,
        e.team_id,
        t.brand as team_brand,
        e.player_id,
        p.name as player_name,
        e.opponent_team_id,
        e.period_id,
        (e.entity->>'start')::numeric as start_seconds,
        (e.entity->>'end')::numeric as end_seconds,
        (e.entity->>'duration')::numeric as duration_seconds,
        (e.entity->>'start_frame')::integer as start_frame,
        (e.entity->>'end_frame')::integer as end_frame,
        (e.entity->>'start_x')::numeric as start_x,
        (e.entity->>'start_y')::numeric as start_y,
        (e.entity->>'end_x')::numeric as end_x,
        (e.entity->>'end_y')::numeric as end_y,
        (e.entity->>'contact_height')::numeric as contact_height,
        (e.entity->>'contact_height_category')::text as contact_height_category,
        (e.entity->>'gata_display_name')::text as gata_display_name,
        e.entity
    FROM events e
    LEFT JOIN games g ON e.game_id = g.id
    LEFT JOIN teams t ON e.team_id = t.id
    LEFT JOIN players p ON e.player_id = p.id
    WHERE e.entity->>'gata_display_name' = 'Clearance'
    ORDER BY g.starts_at DESC, e.period_id DESC
    """)


def downgrade() -> None:
    # Drop the view
    op.execute("DROP VIEW IF EXISTS v_clearance_events_detailed")
