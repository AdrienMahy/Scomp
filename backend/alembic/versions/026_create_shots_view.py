"""Create v_shots view - Shot events only with all relevant fields.

Revision ID: 026_create_shots_view
Revises: 025_fix_events_full_type_casts
Create Date: 2026-09-07 11:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '026_create_shots_view'
down_revision = '025_fix_events_full_type_casts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE VIEW v_shots AS
    SELECT 
        -- Core event fields
        e.id,
        e.game_id,
        e.period_id,
        e.player_id,
        e.team_id,
        e.opponent_team_id,
        e.goalkeeper_id,
        e.possession_id,
        e.phase_of_play_id,
        
        -- Game context
        g.name as game_name,
        g.competition_id,
        c.name as competition_name,
        t.name as team_name,
        ot.name as opponent_team_name,
        p.name as player_name,
        gk.name as goalkeeper_name,
        
        -- Shot event type
        e.entity->>'gata_display_name' as event_type,
        
        -- Positioning data
        e.entity->>'start_x' as start_x,
        e.entity->>'start_y' as start_y,
        e.entity->>'end_x' as end_x,
        e.entity->>'end_y' as end_y,
        e.entity->>'distance_to_goal' as distance_to_goal,
        e.entity->>'finishing_zone' as finishing_zone,
        e.entity->>'tactical_space' as tactical_space,
        e.entity->>'tactical_subspace' as tactical_subspace,
        e.entity->>'pre_shot_dominant_corridor' as pre_shot_dominant_corridor,
        
        -- Shot outcome
        e.entity->>'scored' as scored,
        e.entity->>'on_target' as on_target,
        e.entity->>'saved' as saved,
        e.entity->>'woodwork' as woodwork,
        e.entity->>'xg' as xg_value,
        e.entity->>'header' as is_header,
        e.entity->>'penalty' as is_penalty,
        e.entity->>'big_chances' as is_big_chance,
        e.entity->>'chances' as is_chance,
        
        -- Shot quality
        e.entity->>'chance_quality' as chance_quality,
        e.entity->>'body_part' as body_part,
        
        -- Box location
        e.entity->>'in_box' as in_box,
        e.entity->>'in_six_yard_box' as in_six_yard_box,
        
        -- Assist information
        e.entity->>'assist' as assist_id,
        e.entity->>'assisted' as is_assisted,
        e.entity->>'cross_assisted' as is_cross_assisted,
        e.entity->>'direct_assist' as is_direct_assist,
        e.entity->>'from_cross' as from_cross,
        
        -- Context
        e.entity->>'one_touch' as is_one_touch,
        e.entity->>'set_piece_shot' as is_set_piece,
        e.entity->>'under_pressure' as under_pressure,
        e.entity->>'pressure_level' as pressure_level,
        e.entity->>'available_time' as available_time_seconds,
        
        -- Goalkeeper context
        e.entity->>'goalkeeper_1v1' as goalkeeper_1v1,
        e.entity->>'goalkeeper_goal_conceded' as goalkeeper_goal_conceded,
        e.entity->>'goalkeeper_saves' as goalkeeper_saves,
        
        -- Attack context
        e.entity->>'n_attackers_in_box' as n_attackers_in_box,
        e.entity->>'attackers_in_box' as attackers_in_box_json,
        
        -- Defense context
        e.entity->>'n_defenders_in_box' as n_defenders_in_box,
        e.entity->>'defenders_in_box' as defenders_in_box_json,
        e.entity->>'coverage_defenders' as coverage_defenders_json,
        e.entity->>'closest_defender_to_shot' as closest_defender_id,
        
        -- Play context
        e.entity->>'phase_of_play_label' as phase_of_play_label,
        e.entity->>'play_label' as play_label,
        e.entity->>'possession_label' as possession_label,
        e.entity->>'counter_attack_conceded' as counter_attack_conceded,
        
        -- Sequence context
        e.entity->>'individual_possession' as individual_possession_id,
        e.entity->>'sequence_id' as sequence_id,
        e.entity->>'sequence_end' as sequence_end_time,
        
        -- Tactical context
        e.entity->>'1v1_situation' as is_1v1_situation,
        
        -- Timing
        e.entity->>'start' as start_time,
        e.entity->>'end' as end_time,
        e.entity->>'duration' as duration_seconds,
        e.entity->>'start_frame' as start_frame,
        e.entity->>'end_frame' as end_frame,
        
        -- IDs from entity
        e.entity->>'play' as play_id,
        e.entity->>'phase_of_play' as phase_of_play_uuid,
        e.entity->>'possession' as possession_uuid,
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
    LEFT JOIN players gk ON e.goalkeeper_id = gk.id
    WHERE e.entity->>'gata_display_name' = 'Shot'
    AND e.entity IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute('DROP VIEW IF EXISTS v_shots CASCADE;')
