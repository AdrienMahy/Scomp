"""Create unified v_setpieces_all_detailed view combining all specialized views

Revision ID: 057
Revises: 056
Create Date: 2026-09-15 10:55:00.000000

Purpose:
    - Create v_setpieces_all_detailed: UNION of all specialized setpiece views
    - Provides single view with all setpieces and their type-specific data
    - Easier for general queries while still having full detail
    - Keeps specialized views for performance if needed
"""

from alembic import op


revision = '057'
down_revision = '056'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create v_setpieces_all_detailed view"""
    
    op.execute("""
    DROP VIEW IF EXISTS v_setpieces_all_detailed CASCADE
    """)
    
    op.execute("""
    CREATE VIEW v_setpieces_all_detailed AS
    
    -- FREE KICKS (Free-kick + Direct free-kick)
    SELECT 
        'FREE_KICK' as setpiece_type_category,
        'free_kick' as detail_column_prefix,
        sp.id, sp.game_id, g.name as game_name, g.starts_at::date as game_date, g.round,
        sp.period_id,
        (sp.time->>'start')::numeric as time_start,
        (sp.time->>'end')::numeric as time_end,
        (sp.time->>'duration')::numeric as time_duration,
        (sp.time->>'start_frame')::integer as time_start_frame,
        (sp.time->>'end_frame')::integer as time_end_frame,
        sp.gata_display_name as entity_subtype,
        (sp.entity->>'type')::text as entity_type,
        (sp.spatial->>'angle')::numeric as spatial_angle,
        (sp.spatial->>'distance')::numeric as spatial_distance,
        sp.player_id, p.name as player_name, p.positions::text as player_position,
        sp.team_id, t.name as team_name, t.brand as team_brand,
        sp.opponent_team_id, ot.name as opponent_team_name, ot.brand as opponent_team_brand,
        (sp.actors->>'targeted_player')::text as targeted_player_id,
        (sp.actors->>'goalkeeper')::text as goalkeeper_id,
        (sp.actors->>'first_contact_player')::text as first_contact_player_id,
        (sp.phase->>'possession')::text as possession_id,
        (sp.phase->>'type_of_play')::text as type_of_play_id,
        (sp.phase->>'phase_of_play')::text as phase_of_play_id,
        (sp.channel->>'start_channel')::text as channel_start,
        (sp.channel->>'end_channel')::text as channel_end,
        sp.free_kick->>'link' as type_specific_link,
        sp.free_kick->>'type' as type_specific_type,
        sp.free_kick->'meta' as type_specific_meta,
        sp.created_at, sp.updated_at,
        sp.free_kick as full_type_specific_jsonb
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.team_id::text = t.id::text
    LEFT JOIN teams ot ON sp.opponent_team_id::text = ot.id::text
    LEFT JOIN players p ON sp.player_id::text = p.id::text
    WHERE sp.gata_display_name IN ('Free-kick', 'Direct free-kick')
    
    UNION ALL
    
    -- CORNER KICKS
    SELECT 
        'CORNER_KICK' as setpiece_type_category,
        'corner_kick' as detail_column_prefix,
        sp.id, sp.game_id, g.name, g.starts_at::date, g.round,
        sp.period_id,
        (sp.time->>'start')::numeric, (sp.time->>'end')::numeric,
        (sp.time->>'duration')::numeric, (sp.time->>'start_frame')::integer,
        (sp.time->>'end_frame')::integer,
        sp.gata_display_name, (sp.entity->>'type')::text,
        (sp.spatial->>'angle')::numeric, (sp.spatial->>'distance')::numeric,
        sp.player_id, p.name, p.positions::text,
        sp.team_id, t.name, t.brand,
        sp.opponent_team_id, ot.name, ot.brand,
        (sp.actors->>'targeted_player')::text,
        (sp.actors->>'goalkeeper')::text,
        (sp.actors->>'first_contact_player')::text,
        (sp.phase->>'possession')::text,
        (sp.phase->>'type_of_play')::text,
        (sp.phase->>'phase_of_play')::text,
        (sp.channel->>'start_channel')::text,
        (sp.channel->>'end_channel')::text,
        sp.corner_kick->>'type' as type_specific_link,
        sp.corner_kick->>'outcome' as type_specific_type,
        sp.corner_kick->'meta' as type_specific_meta,
        sp.created_at, sp.updated_at,
        sp.corner_kick
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.team_id::text = t.id::text
    LEFT JOIN teams ot ON sp.opponent_team_id::text = ot.id::text
    LEFT JOIN players p ON sp.player_id::text = p.id::text
    WHERE sp.gata_display_name = 'Corner kick'
    
    UNION ALL
    
    -- THROW-INS
    SELECT 
        'THROW_IN' as setpiece_type_category,
        'throw_in' as detail_column_prefix,
        sp.id, sp.game_id, g.name, g.starts_at::date, g.round,
        sp.period_id,
        (sp.time->>'start')::numeric, (sp.time->>'end')::numeric,
        (sp.time->>'duration')::numeric, (sp.time->>'start_frame')::integer,
        (sp.time->>'end_frame')::integer,
        sp.gata_display_name, (sp.entity->>'type')::text,
        (sp.spatial->>'angle')::numeric, (sp.spatial->>'distance')::numeric,
        sp.player_id, p.name, p.positions::text,
        sp.team_id, t.name, t.brand,
        sp.opponent_team_id, ot.name, ot.brand,
        (sp.actors->>'targeted_player')::text,
        NULL::text,
        (sp.actors->>'first_contact_player')::text,
        (sp.phase->>'possession')::text,
        (sp.phase->>'type_of_play')::text,
        (sp.phase->>'phase_of_play')::text,
        (sp.channel->>'start_channel')::text,
        (sp.channel->>'end_channel')::text,
        sp.throw_in->>'link', sp.throw_in->>'type',
        sp.throw_in->'meta',
        sp.created_at, sp.updated_at,
        sp.throw_in
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.team_id::text = t.id::text
    LEFT JOIN teams ot ON sp.opponent_team_id::text = ot.id::text
    LEFT JOIN players p ON sp.player_id::text = p.id::text
    WHERE sp.gata_display_name = 'Throw-in'
    
    UNION ALL
    
    -- INDIRECT FREE-KICKS
    SELECT 
        'INDIRECT_FREE_KICK' as setpiece_type_category,
        'indirect_free_kick' as detail_column_prefix,
        sp.id, sp.game_id, g.name, g.starts_at::date, g.round,
        sp.period_id,
        (sp.time->>'start')::numeric, (sp.time->>'end')::numeric,
        (sp.time->>'duration')::numeric, (sp.time->>'start_frame')::integer,
        (sp.time->>'end_frame')::integer,
        sp.gata_display_name, (sp.entity->>'type')::text,
        (sp.spatial->>'angle')::numeric, (sp.spatial->>'distance')::numeric,
        sp.player_id, p.name, p.positions::text,
        sp.team_id, t.name, t.brand,
        sp.opponent_team_id, ot.name, ot.brand,
        (sp.actors->>'targeted_player')::text,
        (sp.actors->>'goalkeeper')::text,
        NULL::text,
        (sp.phase->>'possession')::text,
        (sp.phase->>'type_of_play')::text,
        (sp.phase->>'phase_of_play')::text,
        (sp.channel->>'start_channel')::text,
        (sp.channel->>'end_channel')::text,
        sp.indirect_free_kick->>'type', sp.indirect_free_kick->>'outcome',
        sp.indirect_free_kick->'meta',
        sp.created_at, sp.updated_at,
        sp.indirect_free_kick
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.team_id::text = t.id::text
    LEFT JOIN teams ot ON sp.opponent_team_id::text = ot.id::text
    LEFT JOIN players p ON sp.player_id::text = p.id::text
    WHERE sp.gata_display_name = 'Indirect free-kick'
    
    UNION ALL
    
    -- DIRECT THROW-INS
    SELECT 
        'DIRECT_THROW_IN' as setpiece_type_category,
        'direct_throw_in' as detail_column_prefix,
        sp.id, sp.game_id, g.name, g.starts_at::date, g.round,
        sp.period_id,
        (sp.time->>'start')::numeric, (sp.time->>'end')::numeric,
        (sp.time->>'duration')::numeric, (sp.time->>'start_frame')::integer,
        (sp.time->>'end_frame')::integer,
        sp.gata_display_name, (sp.entity->>'type')::text,
        (sp.spatial->>'angle')::numeric, (sp.spatial->>'distance')::numeric,
        sp.player_id, p.name, p.positions::text,
        sp.team_id, t.name, t.brand,
        sp.opponent_team_id, ot.name, ot.brand,
        (sp.actors->>'targeted_player')::text,
        NULL::text,
        (sp.actors->>'first_contact_player')::text,
        (sp.phase->>'possession')::text,
        (sp.phase->>'type_of_play')::text,
        (sp.phase->>'phase_of_play')::text,
        (sp.channel->>'start_channel')::text,
        (sp.channel->>'end_channel')::text,
        sp.direct_throw_in->>'type', sp.direct_throw_in->>'outcome',
        sp.direct_throw_in->'meta',
        sp.created_at, sp.updated_at,
        sp.direct_throw_in
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.team_id::text = t.id::text
    LEFT JOIN teams ot ON sp.opponent_team_id::text = ot.id::text
    LEFT JOIN players p ON sp.player_id::text = p.id::text
    WHERE sp.gata_display_name IN ('Direct Throw-in', 'Direct throw-in')
    
    ORDER BY game_date DESC, period_id DESC, time_start DESC
    """)


def downgrade() -> None:
    """Drop v_setpieces_all_detailed view"""
    op.execute("DROP VIEW IF EXISTS v_setpieces_all_detailed CASCADE")
