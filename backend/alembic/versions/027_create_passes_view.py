"""Create v_passes view - Pass events only with all relevant fields.

Revision ID: 027_create_passes_view
Revises: 026_create_shots_view
Create Date: 2026-09-07 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '027_create_passes_view'
down_revision = '026_create_shots_view'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create v_passes view - Pass events with 80+ relevant fields
    op.execute("""
        CREATE OR REPLACE VIEW v_passes AS
        SELECT
            -- Core IDs
            e.id as event_id,
            g.id as game_id,
            e.period_id,
            e.player_id as passer_id,
            e.team_id,
            e.opponent_team_id,
            e.targeted_player_id as receiver_id,
            e.possession_id,
            e.phase_of_play_id,
            
            -- Context (from JOINs)
            g.name as game_name,
            g.competition_id,
            c.name as competition_name,
            t.name as team_name,
            ot.name as opponent_team_name,
            p.name as player_name,
            rp.name as receiver_name,
            
            -- Positioning (Start & End)
            e.entity->>'start_x' as start_x,
            e.entity->>'start_y' as start_y,
            e.entity->>'end_x' as end_x,
            e.entity->>'end_y' as end_y,
            e.entity->>'distance' as distance,
            e.entity->>'angle' as angle,
            e.entity->>'height' as height,
            e.entity->>'distance_gained' as distance_gained,
            e.entity->>'distance_gained_pct' as distance_gained_pct,
            
            -- Zones: Start
            e.entity->>'start_third' as start_third,
            e.entity->>'start_channel' as start_channel,
            e.entity->>'tactical_space_start' as tactical_space_start,
            e.entity->>'tactical_subspace_start' as tactical_subspace_start,
            e.entity->>'functional_start_zone' as functional_start_zone,
            e.entity->>'back_line_channel' as back_line_channel,
            
            -- Zones: End
            e.entity->>'end_third' as end_third,
            e.entity->>'end_channel' as end_channel,
            e.entity->>'tactical_space_end' as tactical_space_end,
            e.entity->>'tactical_subspace_end' as tactical_subspace_end,
            e.entity->>'functional_end_zone' as functional_end_zone,
            
            -- Pass Type & Characteristics
            e.entity->>'height_category' as height_category,
            e.entity->>'direction' as direction,
            e.entity->>'distance_category' as distance_category,
            e.entity->>'short_distribution' as short_distribution,
            e.entity->>'through_pass' as through_pass,
            e.entity->>'flick_on' as flick_on,
            e.entity->>'lay_off' as lay_off,
            e.entity->>'return_pass' as return_pass,
            e.entity->>'combination' as combination,
            e.entity->>'one_touch' as one_touch,
            e.entity->>'is_cross' as is_cross,
            e.entity->>'key_pass' as key_pass,
            e.entity->>'progressive_pass' as progressive_pass,
            e.entity->>'penetrative_pass' as penetrative_pass,
            e.entity->>'pass_under_pressure' as pass_under_pressure,
            e.entity->>'switch_of_play' as switch_of_play,
            e.entity->>'pass_towards_half_spaces' as pass_towards_half_spaces,
            e.entity->>'pass_between_the_lines' as pass_between_the_lines,
            e.entity->>'pass_in_behind' as pass_in_behind,
            e.entity->>'in_behind' as in_behind,
            
            -- Pass Outcome & Quality
            e.entity->>'success' as success,
            e.entity->>'blocked' as blocked,
            e.entity->>'one_two' as one_two,
            e.entity->>'direct_play' as direct_play,
            e.entity->>'restart' as restart,
            e.entity->>'restart_type' as restart_type,
            e.entity->>'assist' as assist,
            e.entity->>'direct' as direct,
            
            -- Receiver Context
            e.entity->>'reception_height' as reception_height,
            e.entity->>'reception_height_category' as reception_height_category,
            e.entity->>'receiver_available_time' as receiver_available_time,
            e.entity->>'receiver_pressure_level' as receiver_pressure_level,
            e.entity->>'receiver_under_pressure' as receiver_under_pressure,
            e.entity->>'receiver_keeps_possession' as receiver_keeps_possession,
            
            -- Passer Context
            e.entity->>'pressure_level' as pressure_level,
            e.entity->>'under_pressure' as under_pressure,
            e.entity->>'available_time' as available_time,
            e.entity->>'goalkeeper_pass' as goalkeeper_pass,
            e.entity->>'goalkeeper' as goalkeeper,
            
            -- Players Bypassed
            e.entity->>'n_players_bypassed' as n_players_bypassed,
            e.entity->>'n_players_to_bypass_at_start' as n_players_to_bypass_at_start,
            e.entity->>'n_players_to_bypass_at_end' as n_players_to_bypass_at_end,
            e.entity->>'players_bypassed' as players_bypassed_json,
            e.entity->>'players_to_bypass_at_start' as players_to_bypass_at_start_json,
            e.entity->>'players_to_bypass_at_end' as players_to_bypass_at_end_json,
            e.entity->>'opponent_pressers' as opponent_pressers_json,
            e.entity->>'expected_defender_at_arrival' as expected_defender_at_arrival,
            
            -- Play Context
            e.entity->>'possession_label' as possession_label,
            e.entity->>'play_label' as play_label,
            e.entity->>'phase_of_play_label' as phase_of_play_label,
            
            -- Build-up Play
            e.entity->>'gk_high_build_up' as gk_high_build_up,
            e.entity->>'short_distribution' as short_distribution_2,
            e.entity->>'breaking_front_line_attempt' as breaking_front_line_attempt,
            e.entity->>'breaking_midfield_line_attempt' as breaking_midfield_line_attempt,
            
            -- Chain Involvement
            e.entity->>'goal_chain_link' as goal_chain_link,
            e.entity->>'shot_chain_link' as shot_chain_link,
            e.entity->>'goal_chain_involvement' as goal_chain_involvement,
            e.entity->>'shot_chain_involvement' as shot_chain_involvement,
            e.entity->>'goal_within_10s' as goal_within_10s,
            e.entity->>'shot_within_10s' as shot_within_10s,
            e.entity->>'box_entry_trigger' as box_entry_trigger,
            e.entity->>'box_entry_within_10s' as box_entry_within_10s,
            
            -- Timing
            e.entity->>'start' as start_time,
            e.entity->>'end' as end_time,
            e.entity->>'duration' as duration,
            e.entity->>'start_frame' as start_frame,
            e.entity->>'end_frame' as end_frame,
            
            -- Sequence & Possession
            e.entity->>'sequence_id' as sequence_id,
            e.entity->>'possession' as possession_uuid,
            e.entity->>'individual_possession' as individual_possession_uuid,
            e.entity->>'receiver_individual_possession' as receiver_individual_possession_uuid,
            e.entity->>'play' as play_uuid,
            e.entity->>'phase_of_play' as phase_of_play_uuid,
            e.entity->>'entity_id' as entity_uuid,
            
            -- Metadata
            e.created_at,
            e.updated_at
        FROM events e
        LEFT JOIN games g ON e.game_id = g.id
        LEFT JOIN competitions c ON g.competition_id = c.id
        LEFT JOIN teams t ON e.team_id = t.id
        LEFT JOIN teams ot ON e.opponent_team_id = ot.id
        LEFT JOIN players p ON e.player_id = p.id
        LEFT JOIN players rp ON e.targeted_player_id = rp.id
        WHERE e.entity->>'gata_display_name' = 'Pass'
        AND e.entity IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_passes")
