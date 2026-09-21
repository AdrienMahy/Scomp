"""Fix v_events_full view - remove problematic type casts.

Revision ID: 025_fix_events_full_type_casts
Revises: 024_fix_events_full_view
Create Date: 2026-09-07 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '025_fix_events_full_type_casts'
down_revision = '024_fix_events_full_view'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the broken view
    op.execute('DROP VIEW IF EXISTS v_events_full CASCADE;')
    
    # Create corrected view - NO TYPE CASTS, keep everything as text
    op.execute("""
    CREATE OR REPLACE VIEW v_events_full AS
    SELECT 
        -- Core event fields
        e.id,
        e.game_id,
        e.period_id,
        e.player_id,
        e.team_id,
        e.opponent_team_id,
        e.targeted_player_id,
        e.goalkeeper_id,
        e.possession_id,
        e.type_of_play_id,
        e.phase_of_play_id,
        
        -- Game context
        g.name as game_name,
        g.competition_id,
        c.name as competition_name,
        t.name as team_name,
        ot.name as opponent_team_name,
        
        -- Entity JSON - Main event action data (all as TEXT - no problematic casts)
        e.entity->>'gata_display_name' as event_type,
        e.entity->>'success' as is_successful,
        e.entity->>'under_pressure' as under_pressure,
        e.entity->>'duration' as duration_seconds,
        e.entity->>'distance' as distance_meters,
        
        -- Positioning data (extracted from entity)
        e.entity->>'start_x' as start_x,
        e.entity->>'start_y' as start_y,
        e.entity->>'end_x' as end_x,
        e.entity->>'end_y' as end_y,
        e.entity->>'angle' as angle_degrees,
        e.entity->>'start_channel' as start_channel,
        e.entity->>'end_channel' as end_channel,
        e.entity->>'start_third' as start_third,
        e.entity->>'end_third' as end_third,
        
        -- Play context
        e.entity->>'play_label' as play_label,
        e.entity->>'phase_of_play_label' as phase_of_play_label,
        e.entity->>'possession_label' as possession_label,
        e.entity->>'direction' as direction,
        
        -- Pass-specific data (extracted from entity)
        e.entity->>'pass_in_behind' as pass_in_behind,
        e.entity->>'key_pass' as is_key_pass,
        e.entity->>'is_cross' as is_cross,
        e.entity->>'through_pass' as is_through_pass,
        e.entity->>'progressive_pass' as is_progressive_pass,
        e.entity->>'assist' as is_assist,
        e.entity->>'one_touch' as is_one_touch,
        
        -- Shot-related data
        e.entity->>'height' as height_category,
        e.entity->>'reception_height_category' as reception_height_category,
        
        -- Defense-related
        e.entity->>'blocked' as is_blocked,
        e.entity->>'pressure_level' as pressure_level,
        e.entity->>'players_bypassed' as players_bypassed_count,
        
        -- Goalkeeper data
        e.entity->>'goalkeeper' as is_goalkeeper_event,
        e.entity->>'goalkeeper_pass' as is_goalkeeper_pass,
        e.entity->>'gk_high_build_up' as is_high_build_up,
        
        -- Strategic context
        e.entity->>'restart' as is_restart,
        e.entity->>'restart_type' as restart_type,
        e.entity->>'switch_of_play' as is_switch_of_play,
        e.entity->>'direct_play' as is_direct_play,
        e.entity->>'combination' as is_combination,
        
        -- Goal-related events
        e.entity->>'goal_within_10s' as goal_within_10s,
        e.entity->>'goal_chain_link' as goal_chain_link,
        e.entity->>'goal_chain_involvement' as goal_chain_involvement,
        e.entity->>'goal_chain_involvement_rank' as goal_chain_involvement_rank,
        
        -- Shot-related events
        e.entity->>'shot_within_10s' as shot_within_10s,
        e.entity->>'shot_chain_link' as shot_chain_link,
        e.entity->>'shot_chain_involvement' as shot_chain_involvement,
        e.entity->>'shot_chain_involvement_rank' as shot_chain_involvement_rank,
        
        -- Box entry
        e.entity->>'box_entry_trigger' as box_entry_trigger,
        e.entity->>'box_entry_within_10s' as box_entry_within_10s,
        
        -- Advanced metrics
        e.entity->>'penetrative_pass' as is_penetrative_pass,
        e.entity->>'pass_between_the_lines' as is_pass_between_lines,
        e.entity->>'pass_towards_half_spaces' as is_pass_to_half_spaces,
        e.entity->>'distance_gained' as distance_gained_meters,
        e.entity->>'distance_gained_pct' as distance_gained_percent,
        e.entity->>'available_time' as available_time_seconds,
        e.entity->>'receiver_available_time' as receiver_available_time_seconds,
        
        -- Pressure context
        e.entity->>'receiver_pressure_level' as receiver_pressure_level,
        e.entity->>'receiver_under_pressure' as receiver_under_pressure,
        e.entity->>'receiver_keeps_possession' as receiver_keeps_possession,
        e.entity->>'pass_under_pressure' as pass_under_pressure,
        
        -- Tactical zones
        e.entity->>'functional_start_zone' as functional_start_zone,
        e.entity->>'functional_end_zone' as functional_end_zone,
        e.entity->>'tactical_space_start' as tactical_space_start,
        e.entity->>'tactical_space_end' as tactical_space_end,
        e.entity->>'tactical_subspace_start' as tactical_subspace_start,
        e.entity->>'tactical_subspace_end' as tactical_subspace_end,
        
        -- Defensive breaking
        e.entity->>'breaking_front_line_attempt' as front_line_breaking_attempt,
        e.entity->>'breaking_midfield_line_attempt' as midfield_line_breaking_attempt,
        
        -- Receiver context
        e.entity->>'n_players_to_bypass_at_start' as n_players_to_bypass_start,
        e.entity->>'n_players_to_bypass_at_end' as n_players_to_bypass_end,
        e.entity->>'n_players_bypassed' as n_players_bypassed,
        e.entity->>'back_line_channel' as back_line_channel,
        
        -- Time references
        e.entity->>'start_frame' as start_frame,
        e.entity->>'end_frame' as end_frame,
        e.entity->>'period_id' as entity_period_id,
        
        -- IDs from entity
        e.entity->>'passer' as passer_id,
        e.entity->>'targeted_player' as targeted_player_entity_id,
        e.entity->>'expected_defender_at_arrival' as expected_defender_id,
        e.entity->>'previous_passer' as previous_passer_id,
        e.entity->>'play' as play_id,
        e.entity->>'entity_id' as entity_uuid,
        e.entity->>'possession' as possession_uuid,
        e.entity->>'sequence_id' as sequence_uuid,
        e.entity->>'phase_of_play' as phase_of_play_uuid,
        e.entity->>'individual_possession' as individual_possession_uuid,
        
        -- Custom/French-specific
        e.entity->>'custom_passes_dans_le_couloir' as custom_passes_couloir,
        
        -- Metadata
        e.created_at,
        e.updated_at
    FROM events e
    LEFT JOIN games g ON e.game_id = g.id
    LEFT JOIN competitions c ON g.competition_id = c.id
    LEFT JOIN teams t ON e.team_id = t.id
    LEFT JOIN teams ot ON e.opponent_team_id = ot.id
    WHERE e.entity IS NOT NULL;
    """)


def downgrade() -> None:
    # Drop the corrected view
    op.execute('DROP VIEW IF EXISTS v_events_full CASCADE;')
    
    # Restore previous version
    op.execute("""
    CREATE OR REPLACE VIEW v_events_full AS
    SELECT 
        -- Core event fields
        e.id,
        e.game_id,
        e.period_id,
        e.player_id,
        e.team_id,
        e.opponent_team_id,
        e.targeted_player_id,
        e.goalkeeper_id,
        e.possession_id,
        e.type_of_play_id,
        e.phase_of_play_id,
        
        -- Game context
        g.name as game_name,
        g.competition_id,
        c.name as competition_name,
        t.name as team_name,
        ot.name as opponent_team_name,
        
        -- Entity JSON - Main event action data
        e.entity->>'gata_display_name' as event_type,
        (e.entity->>'success')::BOOLEAN as is_successful,
        (e.entity->>'under_pressure')::BOOLEAN as under_pressure,
        (e.entity->>'duration')::FLOAT as duration_seconds,
        (e.entity->>'distance')::FLOAT as distance_meters,
        
        -- Positioning data (extracted from entity)
        (e.entity->>'start_x')::FLOAT as start_x,
        (e.entity->>'start_y')::FLOAT as start_y,
        (e.entity->>'end_x')::FLOAT as end_x,
        (e.entity->>'end_y')::FLOAT as end_y,
        (e.entity->>'angle')::FLOAT as angle_degrees,
        e.entity->>'start_channel' as start_channel,
        e.entity->>'end_channel' as end_channel,
        e.entity->>'start_third' as start_third,
        e.entity->>'end_third' as end_third,
        
        -- Play context
        e.entity->>'play_label' as play_label,
        e.entity->>'phase_of_play_label' as phase_of_play_label,
        e.entity->>'possession_label' as possession_label,
        e.entity->>'direction' as direction,
        
        -- Pass-specific data (extracted from entity)
        e.entity->>'pass_in_behind' as pass_in_behind,
        e.entity->>'key_pass' as is_key_pass,
        e.entity->>'is_cross' as is_cross,
        e.entity->>'through_pass' as is_through_pass,
        e.entity->>'progressive_pass' as is_progressive_pass,
        e.entity->>'assist' as is_assist,
        e.entity->>'one_touch' as is_one_touch,
        
        -- Shot-related data
        e.entity->>'height' as height_category,
        e.entity->>'reception_height_category' as reception_height_category,
        
        -- Defense-related
        e.entity->>'blocked' as is_blocked,
        e.entity->>'pressure_level' as pressure_level,
        e.entity->>'players_bypassed' as players_bypassed_count,
        
        -- Goalkeeper data
        (e.entity->>'goalkeeper')::BOOLEAN as is_goalkeeper_event,
        e.entity->>'goalkeeper_pass' as is_goalkeeper_pass,
        e.entity->>'gk_high_build_up' as is_high_build_up,
        
        -- Strategic context
        e.entity->>'restart' as is_restart,
        e.entity->>'restart_type' as restart_type,
        e.entity->>'switch_of_play' as is_switch_of_play,
        e.entity->>'direct_play' as is_direct_play,
        e.entity->>'combination' as is_combination,
        
        -- Goal-related events
        e.entity->>'goal_within_10s' as goal_within_10s,
        e.entity->>'goal_chain_link' as goal_chain_link,
        e.entity->>'goal_chain_involvement' as goal_chain_involvement,
        e.entity->>'goal_chain_involvement_rank' as goal_chain_involvement_rank,
        
        -- Shot-related events
        e.entity->>'shot_within_10s' as shot_within_10s,
        e.entity->>'shot_chain_link' as shot_chain_link,
        e.entity->>'shot_chain_involvement' as shot_chain_involvement,
        e.entity->>'shot_chain_involvement_rank' as shot_chain_involvement_rank,
        
        -- Box entry
        e.entity->>'box_entry_trigger' as box_entry_trigger,
        e.entity->>'box_entry_within_10s' as box_entry_within_10s,
        
        -- Advanced metrics
        e.entity->>'penetrative_pass' as is_penetrative_pass,
        e.entity->>'pass_between_the_lines' as is_pass_between_lines,
        e.entity->>'pass_towards_half_spaces' as is_pass_to_half_spaces,
        e.entity->>'distance_gained' as distance_gained_meters,
        e.entity->>'distance_gained_pct' as distance_gained_percent,
        e.entity->>'available_time' as available_time_seconds,
        e.entity->>'receiver_available_time' as receiver_available_time_seconds,
        
        -- Pressure context
        e.entity->>'receiver_pressure_level' as receiver_pressure_level,
        e.entity->>'receiver_under_pressure' as receiver_under_pressure,
        e.entity->>'receiver_keeps_possession' as receiver_keeps_possession,
        e.entity->>'pass_under_pressure' as pass_under_pressure,
        
        -- Tactical zones
        e.entity->>'functional_start_zone' as functional_start_zone,
        e.entity->>'functional_end_zone' as functional_end_zone,
        e.entity->>'tactical_space_start' as tactical_space_start,
        e.entity->>'tactical_space_end' as tactical_space_end,
        e.entity->>'tactical_subspace_start' as tactical_subspace_start,
        e.entity->>'tactical_subspace_end' as tactical_subspace_end,
        
        -- Defensive breaking
        e.entity->>'breaking_front_line_attempt' as front_line_breaking_attempt,
        e.entity->>'breaking_midfield_line_attempt' as midfield_line_breaking_attempt,
        
        -- Receiver context
        e.entity->>'n_players_to_bypass_at_start' as n_players_to_bypass_start,
        e.entity->>'n_players_to_bypass_at_end' as n_players_to_bypass_end,
        e.entity->>'n_players_bypassed' as n_players_bypassed,
        e.entity->>'back_line_channel' as back_line_channel,
        
        -- Time references
        e.entity->>'start_frame' as start_frame,
        e.entity->>'end_frame' as end_frame,
        e.entity->>'period_id' as entity_period_id,
        
        -- IDs from entity
        e.entity->>'passer' as passer_id,
        e.entity->>'targeted_player' as targeted_player_entity_id,
        e.entity->>'expected_defender_at_arrival' as expected_defender_id,
        e.entity->>'previous_passer' as previous_passer_id,
        e.entity->>'play' as play_id,
        e.entity->>'entity_id' as entity_uuid,
        e.entity->>'possession' as possession_uuid,
        e.entity->>'sequence_id' as sequence_uuid,
        e.entity->>'phase_of_play' as phase_of_play_uuid,
        e.entity->>'individual_possession' as individual_possession_uuid,
        
        -- Custom/French-specific
        e.entity->>'custom_passes_dans_le_couloir' as custom_passes_couloir,
        
        -- Metadata
        e.created_at,
        e.updated_at
    FROM events e
    LEFT JOIN games g ON e.game_id = g.id
    LEFT JOIN competitions c ON g.competition_id = c.id
    LEFT JOIN teams t ON e.team_id = t.id
    LEFT JOIN teams ot ON e.opponent_team_id = ot.id
    WHERE e.entity IS NOT NULL;
    """)
