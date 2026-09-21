"""Increase VARCHAR(50) fields in event tables (phase_of_play, possession_collective, type_of_play, ball_in_play)

Revision ID: 041_increase_event_table_varchar
Revises: 040_force_fitness_varchar_fixes
Create Date: 2026-09-09 12:04:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '041_increase_event_table_varchar'
down_revision = '040_force_fitness_varchar_fixes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase VARCHAR(50) fields in event tables using raw SQL with existence checks"""
    
    # PostgreSQL DO blocks to safely check if columns exist before altering
    
    # ========================================================================
    # PHASE_OF_PLAY TABLE
    # ========================================================================
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='phases_of_play' AND column_name='defensive_block_area'
            ) THEN
                ALTER TABLE phases_of_play ALTER COLUMN defensive_block_area TYPE VARCHAR(100);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='phases_of_play' AND column_name='outcome'
            ) THEN
                ALTER TABLE phases_of_play ALTER COLUMN outcome TYPE VARCHAR(100);
            END IF;
        END$$;
    """)
    
    # ========================================================================
    # POSSESSION_COLLECTIVE TABLE
    # ========================================================================
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='possession_collective' AND column_name='possession_outcome'
            ) THEN
                ALTER TABLE possession_collective ALTER COLUMN possession_outcome TYPE VARCHAR(100);
            END IF;
        END$$;
    """)
    
    # ========================================================================
    # TYPE_OF_PLAY TABLE
    # ========================================================================
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='types_of_play' AND column_name='outcome'
            ) THEN
                ALTER TABLE types_of_play ALTER COLUMN outcome TYPE VARCHAR(100);
            END IF;
        END$$;
    """)
    
    # ========================================================================
    # BALL_IN_PLAY TABLE (if exists)
    # ========================================================================
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='ball_in_play' AND column_name='outcome'
            ) THEN
                ALTER TABLE ball_in_play ALTER COLUMN outcome TYPE VARCHAR(100);
            END IF;
        END$$;
    """)


def downgrade() -> None:
    """Revert VARCHAR fields back to String(50)"""
    
    # Safe downgrades with existence checks
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='phases_of_play' AND column_name='defensive_block_area'
            ) THEN
                ALTER TABLE phases_of_play ALTER COLUMN defensive_block_area TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='phases_of_play' AND column_name='outcome'
            ) THEN
                ALTER TABLE phases_of_play ALTER COLUMN outcome TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='possession_collective' AND column_name='possession_outcome'
            ) THEN
                ALTER TABLE possession_collective ALTER COLUMN possession_outcome TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='types_of_play' AND column_name='outcome'
            ) THEN
                ALTER TABLE types_of_play ALTER COLUMN outcome TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='ball_in_play' AND column_name='outcome'
            ) THEN
                ALTER TABLE ball_in_play ALTER COLUMN outcome TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
