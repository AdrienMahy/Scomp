"""Create VIEW v_events_full - Events table with all JSONB fields extracted

Revision ID: 021_add_events_full_view
Revises: 020_add_gata_display_name
Create Date: 2026-09-07 16:00:00.000000

This migration creates a comprehensive VIEW that extracts all JSONB columns
from the events table, providing flattened access to all fields for easier
querying and analysis.

The view includes:
- All 12 critical columns (player_id, team_id, period_id, etc.)
- All 17 JSONB sections extracted as separate columns
- Relationships enriched with game, player, team, and competition data

Total output: 12 critical + 17 JSONB + enriched context = ~50+ columns

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021_add_events_full_view'
down_revision = '020_add_gata_display_name'
branch_labels = None
depends_on = None


def upgrade():
    """Create v_events_full VIEW with all JSONB extracted"""
    
    op.execute("""
    CREATE OR REPLACE VIEW v_events_full AS
    
    SELECT
      -- ========================================================================
      -- CRITICAL COLUMNS (Indexed for joins)
      -- ========================================================================
      e.id as event_id,
      e.game_id,
      e.period_id,
      e.player_id,
      e.team_id,
      e.opponent_team_id,
      e.targeted_player_id,
      e.goalkeeper_id,
      e.expected_defender_at_arrival_id,
      e.previous_passer_id,
      e.possession_id,
      e.type_of_play_id,
      e.phase_of_play_id,
      e.individual_possession_id,
      
      -- ========================================================================
      -- ENRICHMENT: Game Context
      -- ========================================================================
      g.name as game_name,
      g.played_at,
      g.home_team_id,
      g.away_team_id,
      CASE 
        WHEN g.home_team_id = e.team_id THEN 'HOME'
        WHEN g.away_team_id = e.team_id THEN 'AWAY'
        ELSE NULL
      END as team_side,
      
      -- ========================================================================
      -- ENRICHMENT: Competition & Season
      -- ========================================================================
      c.name as competition_name,
      s.name as season_name,
      g.round_name,
      
      -- ========================================================================
      -- ENRICHMENT: Player & Team Info
      -- ========================================================================
      p.name as player_name,
      t.name as team_name,
      
      -- ========================================================================
      -- JSONB SECTION 1: entity
      -- ========================================================================
      e.entity,
      e.entity->>'id' as entity_id,
      e.entity->>'entityType' as entity_type,
      e.entity->>'period' as entity_period,
      e.entity->>'gata_display_name' as entity_gata_display_name,
      
      -- ========================================================================
      -- JSONB SECTION 2: time
      -- ========================================================================
      e.time,
      (e.time->>'seconds_elapsed')::FLOAT as time_seconds_elapsed,
      (e.time->>'seconds_in_period')::FLOAT as time_seconds_in_period,
      e.time->>'timestamp' as time_timestamp,
      
      -- ========================================================================
      -- JSONB SECTION 3: phase
      -- ========================================================================
      e.phase,
      e.phase->>'id' as phase_id,
      e.phase->>'name' as phase_name,
      
      -- ========================================================================
      -- JSONB SECTION 4: spatial
      -- ========================================================================
      e.spatial,
      (e.spatial->'x'->>'value')::FLOAT as spatial_x,
      (e.spatial->'y'->>'value')::FLOAT as spatial_y,
      e.spatial->'end'->>'x' as spatial_end_x,
      e.spatial->'end'->>'y' as spatial_end_y,
      e.spatial->>'zone' as spatial_zone,
      e.spatial->>'speed' as spatial_speed,
      
      -- ========================================================================
      -- JSONB SECTION 5: actors
      -- ========================================================================
      e.actors,
      
      -- ========================================================================
      -- JSONB SECTION 6: receiver
      -- ========================================================================
      e.receiver,
      e.receiver->>'playerId' as receiver_player_id,
      e.receiver->>'name' as receiver_name,
      
      -- ========================================================================
      -- JSONB SECTION 7: channel
      -- ========================================================================
      e.channel,
      e.channel->>'id' as channel_id,
      e.channel->>'name' as channel_name,
      
      -- ========================================================================
      -- JSONB SECTION 8: adds
      -- ========================================================================
      e.adds,
      
      -- ========================================================================
      -- JSONB SECTION 9: pass_data
      -- ========================================================================
      e.pass_data,
      e.pass_data->>'passType' as pass_type,
      e.pass_data->>'isLive' as pass_is_live,
      e.pass_data->>'isComplete' as pass_is_complete,
      (e.pass_data->>'distance')::FLOAT as pass_distance,
      e.pass_data->>'angle' as pass_angle,
      
      -- ========================================================================
      -- JSONB SECTION 10: custom
      -- ========================================================================
      e.custom,
      
      -- ========================================================================
      -- JSONB SECTION 11: cross
      -- ========================================================================
      e.cross,
      e.cross->>'crossType' as cross_type,
      e.cross->>'isCrossCompleted' as cross_is_completed,
      
      -- ========================================================================
      -- JSONB SECTION 12: shot
      -- ========================================================================
      e.shot,
      e.shot->>'shotType' as shot_type,
      (e.shot->>'xG')::FLOAT as shot_xg,
      e.shot->>'isGoal' as shot_is_goal,
      
      -- ========================================================================
      -- JSONB SECTION 13: boxentry
      -- ========================================================================
      e.boxentry,
      e.boxentry->>'boxEntryType' as boxentry_type,
      
      -- ========================================================================
      -- JSONB SECTION 14: finalthirdentry
      -- ========================================================================
      e.finalthirdentry,
      e.finalthirdentry->>'finalThirdEntryType' as finalthirdentry_type,
      
      -- ========================================================================
      -- JSONB SECTION 15: clearance
      -- ========================================================================
      e.clearance,
      e.clearance->>'clearanceType' as clearance_type,
      
      -- ========================================================================
      -- JSONB SECTION 16: pressure
      -- ========================================================================
      e.pressure,
      e.pressure->>'pressureType' as pressure_type,
      
      -- ========================================================================
      -- JSONB SECTION 17: receivingrun
      -- ========================================================================
      e.receivingrun,
      e.receivingrun->>'receivingRunType' as receivingrun_type
      
    FROM events e
    LEFT JOIN games g ON e.game_id = g.id
    LEFT JOIN competitions c ON g.competition_id = c.id
    LEFT JOIN seasons s ON g.season_id = s.id
    LEFT JOIN players p ON e.player_id = p.id
    LEFT JOIN teams t ON e.team_id = t.id
    
    ORDER BY g.played_at DESC, e.period_id, (e.time->>'seconds_elapsed')::FLOAT;
    """)


def downgrade():
    """Drop v_events_full VIEW"""
    op.execute("DROP VIEW IF EXISTS v_events_full CASCADE")
