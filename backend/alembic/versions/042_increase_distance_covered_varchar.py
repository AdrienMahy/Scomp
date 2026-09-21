"""Increase VARCHAR(50) fields in team_distance_covered and player_distance_covered tables

Revision ID: 042_increase_distance_covered_varchar
Revises: 041_increase_event_table_varchar
Create Date: 2026-09-09 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '042_increase_distance_covered_varchar'
down_revision = '041_increase_event_table_varchar'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase VARCHAR(50) fields in distance_covered tables using raw SQL"""
    
    # ========================================================================
    # TEAM_DISTANCE_COVERED TABLE
    # ========================================================================
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='team_distance_covered' AND column_name='id'
            ) THEN
                ALTER TABLE team_distance_covered ALTER COLUMN id TYPE VARCHAR(200);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='team_distance_covered' AND column_name='game_id'
            ) THEN
                ALTER TABLE team_distance_covered ALTER COLUMN game_id TYPE VARCHAR(200);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='team_distance_covered' AND column_name='team_id'
            ) THEN
                ALTER TABLE team_distance_covered ALTER COLUMN team_id TYPE VARCHAR(200);
            END IF;
        END$$;
    """)
    
    # ========================================================================
    # PLAYER_DISTANCE_COVERED TABLE
    # ========================================================================
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='player_distance_covered' AND column_name='id'
            ) THEN
                ALTER TABLE player_distance_covered ALTER COLUMN id TYPE VARCHAR(200);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='player_distance_covered' AND column_name='game_id'
            ) THEN
                ALTER TABLE player_distance_covered ALTER COLUMN game_id TYPE VARCHAR(200);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='player_distance_covered' AND column_name='player_id'
            ) THEN
                ALTER TABLE player_distance_covered ALTER COLUMN player_id TYPE VARCHAR(200);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='player_distance_covered' AND column_name='team_id'
            ) THEN
                ALTER TABLE player_distance_covered ALTER COLUMN team_id TYPE VARCHAR(200);
            END IF;
        END$$;
    """)


def downgrade() -> None:
    """Revert VARCHAR fields back to String(50)"""
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='team_distance_covered' AND column_name='id'
            ) THEN
                ALTER TABLE team_distance_covered ALTER COLUMN id TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='team_distance_covered' AND column_name='game_id'
            ) THEN
                ALTER TABLE team_distance_covered ALTER COLUMN game_id TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='team_distance_covered' AND column_name='team_id'
            ) THEN
                ALTER TABLE team_distance_covered ALTER COLUMN team_id TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='player_distance_covered' AND column_name='id'
            ) THEN
                ALTER TABLE player_distance_covered ALTER COLUMN id TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='player_distance_covered' AND column_name='game_id'
            ) THEN
                ALTER TABLE player_distance_covered ALTER COLUMN game_id TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='player_distance_covered' AND column_name='player_id'
            ) THEN
                ALTER TABLE player_distance_covered ALTER COLUMN player_id TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
    
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='player_distance_covered' AND column_name='team_id'
            ) THEN
                ALTER TABLE player_distance_covered ALTER COLUMN team_id TYPE VARCHAR(50);
            END IF;
        END$$;
    """)
