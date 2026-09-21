"""Create v_crosses view - Cross events only with all relevant fields.

Revision ID: 028_create_crosses_view
Revises: 027_create_passes_view
Create Date: 2026-09-07 12:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '028_create_crosses_view'
down_revision = '027_create_passes_view'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create v_crosses view - Cross events with 90+ relevant fields
    op.execute("""
        CREATE OR REPLACE VIEW v_crosses AS
        SELECT
            -- Core IDs
            e.id as event_id,
            g.id as game_id,
            e.period_id,
            e.player_id as crosser_id,
            e.team_id,
            e.opponent_team_id,
            e.targeted_player_id as first_receiver_id,
            e.possession_id,
            e.phase_of_play_id,
            
            -- Context (from JOINs)
            g.name as game_name,
            g.competition_id,
            c.name as competition_name,
            t.name as team_name,
            ot.name as opponent_team_name,
            p.name as player_name,
            rp.name as first_receiver_name,
            
            -- Cross Characteristics
            e.entity->>'cross_type' as cross_type,
            e.entity->>'cross_direction' as cross_direction,
            e.entity->>'side' as side,
            e.entity->>'cross_depth_category' as cross_depth_category,
            e.entity->>'cross_from_assist_zone' as cross_from_assist_zone,
            e.entity->>'cutback_cross' as cutback_cross,
            e.entity->>'from_deep_area' as from_deep_area,
            e.entity->>'from_advanced_area' as from_advanced_area,
            
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
            e.entity->>'cross_start_zone' as cross_start_zone,
            
            -- Zones: End
            e.entity->>'end_third' as end_third,
            e.entity->>'end_channel' as end_channel,
            e.entity->>'tactical_space_end' as tactical_space_end,
            e.entity->>'tactical_subspace_end' as tactical_subspace_end,
            e.entity->>'functional_end_zone' as functional_end_zone,
            e.entity->>'cross_end_zone' as cross_end_zone,
            
            -- Cross Outcome & Quality
            e.entity->>'success' as success,
            e.entity->>'blocked' as blocked,
            e.entity->>'assist' as assist,
            e.entity->>'key_pass' as key_pass,
            e.entity->>'one_touch' as one_touch,
            e.entity->>'one_two' as one_two,
            e.entity->>'return_pass' as return_pass,
            
            -- Height & Distance Category
            e.entity->>'height_category' as height_category,
            e.entity->>'distance_category' as distance_category,
            
            -- First Contact (Reception)
            e.entity->>'first_contact_player' as first_contact_player_id,
            e.entity->>'first_contact_is_goal' as first_contact_is_goal,
            e.entity->>'first_contact_is_shot' as first_contact_is_shot,
            e.entity->>'first_contact_shot_xg' as first_contact_shot_xg,
            e.entity->>'offensive_first_contact' as offensive_first_contact,
            e.entity->>'reception_height' as reception_height,
            e.entity->>'reception_height_category' as reception_height_category,
            e.entity->>'receiver_available_time' as receiver_available_time,
            e.entity->>'receiver_pressure_level' as receiver_pressure_level,
            e.entity->>'receiver_under_pressure' as receiver_under_pressure,
            e.entity->>'receiver_keeps_possession' as receiver_keeps_possession,
            
            -- Second Contact
            e.entity->>'second_contact_player' as second_contact_player_id,
            e.entity->>'second_contact_is_goal' as second_contact_is_goal,
            e.entity->>'second_contact_is_shot' as second_contact_is_shot,
            e.entity->>'second_contact_shot_xg' as second_contact_shot_xg,
            e.entity->>'offensive_second_contact' as offensive_second_contact,
            
            -- Crosser Context
            e.entity->>'pressure_level' as pressure_level,
            e.entity->>'under_pressure' as under_pressure,
            e.entity->>'available_time' as available_time,
            e.entity->>'previous_passer' as previous_passer_id,
            
            -- Attackers in Box (Start & End)
            e.entity->>'n_attackers_in_box_at_start' as n_attackers_in_box_at_start,
            e.entity->>'n_attackers_in_box_at_end' as n_attackers_in_box_at_end,
            e.entity->>'attackers_in_box' as attackers_in_box_json,
            e.entity->>'attackers_in_central_box' as attackers_in_central_box_json,
            e.entity->>'attackers_near_post' as attackers_near_post_json,
            e.entity->>'attackers_far_post' as attackers_far_post_json,
            e.entity->>'attackers_edge_of_the_box' as attackers_edge_of_the_box_json,
            e.entity->>'free_attackers_in_box' as free_attackers_in_box_json,
            e.entity->>'n_free_attackers_in_box' as n_free_attackers_in_box,
            e.entity->>'n_attackers_edge_of_box_at_start' as n_attackers_edge_of_box_at_start,
            e.entity->>'n_attackers_edge_of_box_at_end' as n_attackers_edge_of_box_at_end,
            
            -- Defenders in Box (Start & End)
            e.entity->>'n_defenders_in_box_at_start' as n_defenders_in_box_at_start,
            e.entity->>'n_defenders_in_box_at_end' as n_defenders_in_box_at_end,
            e.entity->>'defender_in_box' as defenders_in_box_json,
            e.entity->>'defenders_central_box' as defenders_central_box_json,
            e.entity->>'defenders_near_post' as defenders_near_post_json,
            e.entity->>'defenders_far_post' as defenders_far_post_json,
            e.entity->>'defenders_edge_of_the_box' as defenders_edge_of_the_box_json,
            e.entity->>'target_coverage_defenders' as target_coverage_defenders_json,
            e.entity->>'closest_defender_to_cross' as closest_defender_to_cross_id,
            e.entity->>'expected_defender_at_arrival' as expected_defender_at_arrival,
            e.entity->>'n_defenders_edge_of_box_at_start' as n_defenders_edge_of_box_at_start,
            e.entity->>'n_defenders_edge_of_the_box_at_start' as n_defenders_edge_of_the_box_at_start,
            e.entity->>'n_defenders_edge_of_box_at_end' as n_defenders_edge_of_box_at_end,
            
            -- Player Differences
            e.entity->>'box_player_difference' as box_player_difference,
            e.entity->>'central_box_player_difference' as central_box_player_difference,
            e.entity->>'near_post_player_difference' as near_post_player_difference,
            e.entity->>'far_post_player_difference' as far_post_player_difference,
            e.entity->>'edge_box_player_difference' as edge_box_player_difference,
            
            -- Chain Involvement & Outcomes
            e.entity->>'goal_chain_link' as goal_chain_link,
            e.entity->>'shot_chain_link' as shot_chain_link,
            e.entity->>'goal_in_sequence' as goal_in_sequence,
            e.entity->>'shot_in_sequence' as shot_in_sequence,
            e.entity->>'goal_chain_involvement' as goal_chain_involvement,
            e.entity->>'shot_chain_involvement' as shot_chain_involvement,
            e.entity->>'goal_within_10s' as goal_within_10s,
            e.entity->>'shot_within_10s' as shot_within_10s,
            e.entity->>'n_shots_in_sequence' as n_shots_in_sequence,
            e.entity->>'sequence_xg' as sequence_xg,
            
            -- Context
            e.entity->>'box_entry_trigger' as box_entry_trigger,
            e.entity->>'box_entry_within_10s' as box_entry_within_10s,
            e.entity->>'restart' as restart,
            e.entity->>'restart_type' as restart_type,
            e.entity->>'counter_attack_conceded' as counter_attack_conceded,
            e.entity->>'defensive_first_contact_recovery' as defensive_first_contact_recovery,
            
            -- Play Context
            e.entity->>'possession_label' as possession_label,
            e.entity->>'play_label' as play_label,
            e.entity->>'phase_of_play_label' as phase_of_play_label,
            e.entity->>'goalkeeper' as goalkeeper,
            
            -- Players Bypassed
            e.entity->>'n_players_bypassed' as n_players_bypassed,
            e.entity->>'n_players_to_bypass_at_start' as n_players_to_bypass_at_start,
            e.entity->>'n_players_to_bypass_at_end' as n_players_to_bypass_at_end,
            e.entity->>'players_bypassed' as players_bypassed_json,
            e.entity->>'players_to_bypass_at_start' as players_to_bypass_at_start_json,
            e.entity->>'players_to_bypass_at_end' as players_to_bypass_at_end_json,
            e.entity->>'opponent_pressers' as opponent_pressers_json,
            
            -- Opposition Context
            e.entity->>'free_attackers_zone' as free_attackers_zone_json,
            e.entity->>'offensive_third_contact' as offensive_third_contact,
            
            -- Timing
            e.entity->>'start' as start_time,
            e.entity->>'end' as end_time,
            e.entity->>'duration' as duration,
            e.entity->>'start_frame' as start_frame,
            e.entity->>'end_frame' as end_frame,
            e.entity->>'sequence_end' as sequence_end,
            
            -- Sequence & Possession
            e.entity->>'sequence_id' as sequence_id,
            e.entity->>'possession' as possession_uuid,
            e.entity->>'individual_possession' as individual_possession_uuid,
            e.entity->>'receiver_individual_possession' as receiver_individual_possession_uuid,
            e.entity->>'play' as play_uuid,
            e.entity->>'phase_of_play' as phase_of_play_uuid,
            e.entity->>'pass' as pass_uuid,
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
        WHERE e.entity->>'gata_display_name' = 'Cross'
        AND e.entity IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_crosses")
