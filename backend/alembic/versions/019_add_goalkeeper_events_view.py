"""Create VIEW v_goalkeeper_events - All goalkeeper events from multiple tables

Revision ID: 019_add_goalkeeper_events_view
Revises: 018_clean_slate_with_teams
Create Date: 2026-09-07 14:00:00.000000

This migration creates a VIEW that aggregates all goalkeeper events from:
1. Events table (goalkeeper_id column) - GK as target/subject
2. Events table (player_id) - GK as active player (passes, movements, etc.)
3. GoalKick table - GK taking goal kicks
4. GameCards table - GK receiving cards

The view identifies goalkeepers via lineup_players WHERE position='GK'

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '019_add_goalkeeper_events_view'
down_revision = '018_clean_slate_with_teams'
branch_labels = None
depends_on = None


def upgrade():
    """Create v_goalkeeper_events VIEW"""
    
    op.execute("""
    CREATE OR REPLACE VIEW v_goalkeeper_events AS
    
    WITH gk_players AS (
      -- Master list of all goalkeepers identified by position='GK' in lineups
      SELECT DISTINCT lp.player_id
      FROM lineup_players lp
      WHERE lp.position = 'GK'
    ),
    
    gk_events_raw AS (
      -- ========================================================================
      -- PHASE 1: Events where goalkeeper_id IS NOT NULL
      -- (GK is the target/subject of the action - e.g., save, catch)
      -- ========================================================================
      SELECT 
        e.id as event_id,
        e.game_id,
        e.goalkeeper_id as player_id,
        e.period_id as period,
        e.entity->>'entityType' as event_type,
        'goalkeeper_target' as event_source,
        e.spatial,
        e.time as event_time,
        e.entity,
        e.actors,
        e.team_id
      FROM events e
      WHERE e.goalkeeper_id IS NOT NULL
      
      UNION ALL
      
      -- ========================================================================
      -- PHASE 2: Events where player_id belongs to a goalkeeper
      -- (GK is the active player - e.g., passing, movement)
      -- ========================================================================
      SELECT 
        e.id as event_id,
        e.game_id,
        e.player_id,
        e.period_id as period,
        e.entity->>'entityType' as event_type,
        'goalkeeper_active' as event_source,
        e.spatial,
        e.time as event_time,
        e.entity,
        e.actors,
        e.team_id
      FROM events e
      WHERE e.player_id IN (SELECT player_id FROM gk_players)
      
      UNION ALL
      
      -- ========================================================================
      -- PHASE 3: GoalKick events (GK taking goal kicks)
      -- ========================================================================
      SELECT 
        g.id as event_id,
        g.game_id,
        g.goalkeeper_id as player_id,
        g.period_id as period,
        'GoalKick' as event_type,
        'goal_kick' as event_source,
        g.spatial,
        g.time as event_time,
        g.entity,
        g.actors,
        g.team_id
      FROM goalkick g
      WHERE g.goalkeeper_id IS NOT NULL
      
      UNION ALL
      
      -- ========================================================================
      -- PHASE 4: GameCards (yellow/red cards for goalkeepers)
      -- ========================================================================
      SELECT 
        gc.id as event_id,
        gc.game_id,
        gc.player_id,
        gc.period,
        'Card' as event_type,
        'card' as event_source,
        NULL as spatial,
        JSON_BUILD_OBJECT('card_type', gc.card_type, 'timestamp', gc.timestamp)::JSONB as event_time,
        JSON_BUILD_OBJECT('card_type', gc.card_type)::JSONB as entity,
        NULL as actors,
        gc.team_id
      FROM game_cards gc
      WHERE gc.player_id IN (SELECT player_id FROM gk_players)
    )
    
    -- ========================================================================
    -- FINAL SELECT: Enrich with match and player context
    -- ========================================================================
    SELECT 
      ge.event_id,
      ge.game_id,
      g.name as game_name,
      g.played_at,
      c.name as competition_name,
      s.name as season_name,
      g.round_name,
      ge.player_id,
      p.name as player_name,
      p.first_name,
      p.last_name,
      t.name as team_name,
      ge.team_id,
      ge.event_type,
      ge.event_source,
      ge.period,
      ge.spatial,
      ge.event_time,
      ge.entity,
      ge.actors,
      g.home_team_id,
      g.away_team_id,
      CASE 
        WHEN g.home_team_id = ge.team_id THEN 'HOME'
        WHEN g.away_team_id = ge.team_id THEN 'AWAY'
        ELSE NULL
      END as team_side
    FROM gk_events_raw ge
    LEFT JOIN games g ON ge.game_id = g.id
    LEFT JOIN competitions c ON g.competition_id = c.id
    LEFT JOIN seasons s ON g.season_id = s.id
    LEFT JOIN players p ON ge.player_id = p.id
    LEFT JOIN teams t ON ge.team_id = t.id
    WHERE ge.player_id IS NOT NULL
    ORDER BY g.played_at DESC, ge.period, 
             CASE WHEN ge.event_time->>'seconds_elapsed' IS NOT NULL 
                  THEN (ge.event_time->>'seconds_elapsed')::FLOAT 
                  ELSE 0 END;
    """)


def downgrade():
    """Drop v_goalkeeper_events VIEW"""
    op.execute("DROP VIEW IF EXISTS v_goalkeeper_events CASCADE")
