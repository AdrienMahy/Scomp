"""Restructure setpieces table with enhanced hybrid JSONB schema

Revision ID: 051
Revises: 050
Create Date: 2026-09-12 00:00:00.000000

Migration to restructure setpieces table for improved hybrid schema:

Changes:
1. Add critical extracted columns (BTREE indexed):
   - period_id (for fast period filtering)
   - team_id (FK to teams table)
   - opponent_team_id (FK to teams table)
   - player_id (FK to players table)
   - gata_display_name (VARCHAR, source of truth for type determination)

2. Add core JSONB sections (always present):
   - entity: {id, gata_display_name, type, display_group}
   - time: {start, end, duration, start_frame, end_frame, start_timestamp}
   - spatial: {distance, distance_gained, possession_outcome, location}
   - actors: {player_in_possession, team, opponent_team, players_involved}
   - phase: {phase, phase_time, min:sec, possession_chain}
   - channel: {channel, side, field_zone, area}

3. Add type-specific JSONB sections (only ONE populated per setpiece):
   - corner_kick (for corner kicks)
   - free_kick (for direct free kicks)
   - indirect_free_kick (for indirect free kicks)
   - throw_in (for normal throw-ins)
   - direct_throw_in (for direct throw-ins)

4. Remove old generic 'setpieces' JSONB column (data migrated to type-specific sections)

5. Create new indices:
   - BTREE: game_id+period_id, team_id+period_id, gata_display_name
   - GIN: entity, spatial, actors, corner_kick, free_kick, throw_in (for JSONB queries)

6. Create FK constraints on team_id, opponent_team_id, player_id

7. Recreate dependent views (v_setpieces_detailed)

Benefits:
- Type determination is now authoritative via gata_display_name
- Queries by type can use BTREE index on gata_display_name
- Type-specific sections enable specialized analytics per setpiece type
- Structure matches Events table hybrid pattern for consistency
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '051'
down_revision = '050'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Restructure setpieces table with comprehensive JSONB schema:
    - Add phase, channel JSONB sections
    - Add type-specific sections (corner_kick, free_kick, etc.)
    - Add critical extracted columns for fast queries
    - Remove generic 'setpieces' JSONB column
    """
    
    # ========================================================================
    # Step 1: Backup old data (optional - create view for reference)
    # ========================================================================
    op.execute("""
    CREATE VIEW v_setpieces_backup_old_schema AS
    SELECT * FROM setpieces
    """)
    
    # ========================================================================
    # Step 2: Drop old indices
    # ========================================================================
    op.drop_index('idx_setpiece_game_period', table_name='setpieces')
    
    # ========================================================================
    # Step 3: Drop old views that depend on setpieces
    # ========================================================================
    op.execute("DROP VIEW IF EXISTS v_setpieces_detailed CASCADE")
    
    # ========================================================================
    # Step 4: Add new columns to setpieces table
    # ========================================================================
    
    # Critical extracted columns (for fast BTREE queries)
    op.add_column('setpieces', sa.Column('team_id', sa.String(50), nullable=True, index=True))
    op.add_column('setpieces', sa.Column('opponent_team_id', sa.String(50), nullable=True))
    op.add_column('setpieces', sa.Column('player_id', sa.String(50), nullable=True, index=True))
    op.add_column('setpieces', sa.Column('gata_display_name', sa.String(100), nullable=True, index=True))
    
    # Core JSONB sections (always present)
    op.add_column('setpieces', sa.Column('phase', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('setpieces', sa.Column('channel', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Type-specific JSONB sections (only ONE is populated per setpiece)
    op.add_column('setpieces', sa.Column('corner_kick', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('setpieces', sa.Column('free_kick', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('setpieces', sa.Column('indirect_free_kick', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('setpieces', sa.Column('throw_in', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('setpieces', sa.Column('direct_throw_in', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # ========================================================================
    # Step 5: Populate new columns from existing JSONB data
    # ========================================================================
    
    # Extract team_id, player_id, gata_display_name from existing actors/entity
    op.execute("""
    UPDATE setpieces
    SET 
        team_id = actors->>'team',
        opponent_team_id = actors->>'opponent_team',
        player_id = actors->>'player',
        gata_display_name = entity->>'gata_display_name'
    WHERE team_id IS NULL AND actors IS NOT NULL
    """)
    
    # ========================================================================
    # Step 6a: Drop dependent views before removing column
    # ========================================================================
    op.execute("DROP VIEW IF EXISTS v_setpieces_backup_old_schema")
    
    # ========================================================================
    # Step 6: Drop old 'setpieces' JSONB column (generic data holder)
    # ========================================================================
    op.drop_column('setpieces', 'setpieces')
    
    # ========================================================================
    # Step 7: Create new composite indices for fast queries
    # ========================================================================
    op.create_index('idx_setpiece_game_period', 'setpieces', ['game_id', 'period_id'])
    op.create_index('idx_setpiece_team_period', 'setpieces', ['team_id', 'period_id'])
    op.create_index('idx_setpiece_type', 'setpieces', ['gata_display_name'])
    op.create_index('idx_setpiece_player', 'setpieces', ['player_id'])
    
    # GIN indices for JSONB queries
    op.create_index('idx_setpiece_corner_gin', 'setpieces', ['corner_kick'], postgresql_using='gin')
    op.create_index('idx_setpiece_freekick_gin', 'setpieces', ['free_kick'], postgresql_using='gin')
    op.create_index('idx_setpiece_indirect_gin', 'setpieces', ['indirect_free_kick'], postgresql_using='gin')
    op.create_index('idx_setpiece_throwin_gin', 'setpieces', ['throw_in'], postgresql_using='gin')
    op.create_index('idx_setpiece_directthrowin_gin', 'setpieces', ['direct_throw_in'], postgresql_using='gin')
    op.create_index('idx_setpiece_entity_gin', 'setpieces', ['entity'], postgresql_using='gin')
    op.create_index('idx_setpiece_spatial_gin', 'setpieces', ['spatial'], postgresql_using='gin')
    op.create_index('idx_setpiece_actors_gin', 'setpieces', ['actors'], postgresql_using='gin')
    
    # ========================================================================
    # Step 8: Add foreign key constraints for critical columns
    # ========================================================================
    op.create_foreign_key(
        'fk_setpiece_team',
        'setpieces',
        'teams',
        ['team_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_setpiece_opponent_team',
        'setpieces',
        'teams',
        ['opponent_team_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_setpiece_player',
        'setpieces',
        'players',
        ['player_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # ========================================================================
    # Step 9: Recreate v_setpieces_detailed view with new structure
    # ========================================================================
    op.execute("""
    CREATE VIEW v_setpieces_detailed AS
    SELECT 
        sp.id as setpiece_id,
        sp.game_id,
        g.name as game_name,
        g.starts_at::date as game_date,
        g.round,
        
        -- Period & Timing (from time JSONB)
        sp.period_id,
        (sp.time->>'start')::numeric as start_seconds,
        (sp.time->>'end')::numeric as end_seconds,
        (sp.time->>'duration')::numeric as duration_seconds,
        (sp.time->>'start_frame')::integer as start_frame,
        (sp.time->>'end_frame')::integer as end_frame,
        
        -- Entity & Type
        (sp.entity->>'type')::text as entity_type,
        sp.gata_display_name,
        
        -- Spatial data (distance)
        (sp.spatial->>'distance')::numeric as distance_meters,
        (sp.spatial->>'distance_gained')::numeric as distance_gained,
        
        -- Team & Player info (from critical columns)
        sp.team_id,
        t.brand as team_brand,
        sp.opponent_team_id,
        (SELECT brand FROM teams WHERE id::text = sp.opponent_team_id::text) as opponent_team_brand,
        sp.player_id,
        p.name as player_name,
        
        -- Raw JSONB for reference
        sp.entity,
        sp.time,
        sp.spatial,
        sp.actors,
        sp.phase,
        sp.channel,
        sp.corner_kick,
        sp.free_kick,
        sp.indirect_free_kick,
        sp.throw_in,
        sp.direct_throw_in,
        sp.created_at,
        sp.updated_at
        
    FROM setpieces sp
    LEFT JOIN games g ON sp.game_id::text = g.id::text
    LEFT JOIN teams t ON sp.team_id::text = t.id::text
    LEFT JOIN players p ON sp.player_id::text = p.id::text
    ORDER BY g.starts_at DESC, sp.period_id DESC, (sp.time->>'start')::numeric DESC
    """)


def downgrade() -> None:
    """Rollback to previous schema"""
    
    # Drop new views
    op.execute("DROP VIEW IF EXISTS v_setpieces_detailed CASCADE")
    
    # Drop new foreign keys
    op.drop_constraint('fk_setpiece_player', 'setpieces', type_='foreignkey')
    op.drop_constraint('fk_setpiece_opponent_team', 'setpieces', type_='foreignkey')
    op.drop_constraint('fk_setpiece_team', 'setpieces', type_='foreignkey')
    
    # Drop new indices
    indices_to_drop = [
        'idx_setpiece_game_period',
        'idx_setpiece_team_period',
        'idx_setpiece_type',
        'idx_setpiece_player',
        'idx_setpiece_corner_gin',
        'idx_setpiece_freekick_gin',
        'idx_setpiece_indirect_gin',
        'idx_setpiece_throwin_gin',
        'idx_setpiece_directthrowin_gin',
        'idx_setpiece_entity_gin',
        'idx_setpiece_spatial_gin',
        'idx_setpiece_actors_gin',
    ]
    
    for idx in indices_to_drop:
        op.drop_index(idx, table_name='setpieces')
    
    # Drop new columns
    op.drop_column('setpieces', 'direct_throw_in')
    op.drop_column('setpieces', 'throw_in')
    op.drop_column('setpieces', 'indirect_free_kick')
    op.drop_column('setpieces', 'free_kick')
    op.drop_column('setpieces', 'corner_kick')
    op.drop_column('setpieces', 'channel')
    op.drop_column('setpieces', 'phase')
    op.drop_column('setpieces', 'gata_display_name')
    op.drop_column('setpieces', 'player_id')
    op.drop_column('setpieces', 'opponent_team_id')
    op.drop_column('setpieces', 'team_id')
    
    # Re-add old 'setpieces' JSONB column
    op.add_column('setpieces', sa.Column('setpieces', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Recreate old view
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
