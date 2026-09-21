"""Force increase VARCHAR fields in player_fitness_runs using raw SQL

Revision ID: 040_force_fitness_varchar_fixes
Revises: 039_increase_fitness_string_fields
Create Date: 2026-09-09 12:02:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '040_force_fitness_varchar_fixes'
down_revision = '039_increase_fitness_string_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Force update VARCHAR fields using raw SQL to ensure changes apply"""
    
    # Use raw SQL to force ALTER COLUMN with type changes
    # This bypasses Alembic's existing_type validation which can fail
    
    op.execute("""
        -- Update spatial/tactical String fields from VARCHAR(50) to VARCHAR(100)
        ALTER TABLE player_fitness_runs
        ALTER COLUMN acceleration_intensity_level TYPE VARCHAR(100);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN context TYPE VARCHAR(100);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN direction TYPE VARCHAR(100);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN possession_label TYPE VARCHAR(100);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN start_third TYPE VARCHAR(100);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN end_third TYPE VARCHAR(100);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN start_channel TYPE VARCHAR(100);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN end_channel TYPE VARCHAR(100);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN functional_start_zone TYPE VARCHAR(100);
    """)


def downgrade() -> None:
    """Revert VARCHAR fields back to original sizes"""
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN acceleration_intensity_level TYPE VARCHAR(50);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN context TYPE VARCHAR(50);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN direction TYPE VARCHAR(50);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN possession_label TYPE VARCHAR(50);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN start_third TYPE VARCHAR(50);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN end_third TYPE VARCHAR(50);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN start_channel TYPE VARCHAR(50);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN end_channel TYPE VARCHAR(50);
    """)
    
    op.execute("""
        ALTER TABLE player_fitness_runs
        ALTER COLUMN functional_start_zone TYPE VARCHAR(100);
    """)
