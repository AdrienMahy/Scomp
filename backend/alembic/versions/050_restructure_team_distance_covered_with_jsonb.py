"""Restructure team_distance_covered table with JSONB columns

Revision ID: 050
Revises: 049
Create Date: 2026-09-12

Migration to refactor team_distance_covered table:
- Remove old denormalized float columns: walking_m, jogging_m, moderated_intensity_m, 
  high_intensity_m, sprint_m, in_play_m, out_of_play_m, total_distance_m
- Add new JSONB columns:
  * metrics: { total_distance_m }
  * speed_zones: { walking, jogging, moderated_intensity, high_intensity, sprint }
  * game_state: { in_play, out_of_play }
  * time_intervals: { "0_5": 7373.12, "5_10": ..., "90+": ... }

This enables cleaner API responses and more flexible data querying.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '050'
down_revision = '049'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the migration: add JSONB columns and remove old ones"""
    
    # Step 1: Add new JSONB columns
    op.add_column('team_distance_covered', sa.Column('metrics', sa.JSON, nullable=True))
    op.add_column('team_distance_covered', sa.Column('speed_zones', sa.JSON, nullable=True))
    op.add_column('team_distance_covered', sa.Column('game_state', sa.JSON, nullable=True))
    
    # Step 2: Migrate data from old columns to new JSONB structure
    op.execute("""
        UPDATE team_distance_covered
        SET 
            metrics = jsonb_build_object(
                'total_distance_m', total_distance_m
            ),
            speed_zones = jsonb_build_object(
                'walking', walking_m,
                'jogging', jogging_m,
                'moderated_intensity', moderated_intensity_m,
                'high_intensity', high_intensity_m,
                'sprint', sprint_m
            ),
            game_state = jsonb_build_object(
                'in_play', in_play_m,
                'out_of_play', out_of_play_m
            )
        WHERE total_distance_m IS NOT NULL;
    """)
    
    # Step 3: Convert time_intervals from array to dictionary
    # Array: [{"category_name": "0_5", "distance_m": 7373.12}, ...]
    # Dictionary: {"0_5": 7373.12, "5_10": ...}
    op.execute("""
        UPDATE team_distance_covered
        SET time_intervals = (
            SELECT jsonb_object_agg(
                elem->>'category_name', 
                (elem->>'distance_m')::float
            )
            FROM jsonb_array_elements(time_intervals) AS elem
        )
        WHERE time_intervals IS NOT NULL AND jsonb_typeof(time_intervals) = 'array';
    """)
    
    # Step 4: Drop old float columns
    op.drop_column('team_distance_covered', 'walking_m')
    op.drop_column('team_distance_covered', 'jogging_m')
    op.drop_column('team_distance_covered', 'moderated_intensity_m')
    op.drop_column('team_distance_covered', 'high_intensity_m')
    op.drop_column('team_distance_covered', 'sprint_m')
    op.drop_column('team_distance_covered', 'in_play_m')
    op.drop_column('team_distance_covered', 'out_of_play_m')
    op.drop_column('team_distance_covered', 'total_distance_m')
    
    # Step 5: Make new columns NOT NULL
    op.alter_column('team_distance_covered', 'metrics', nullable=False)
    op.alter_column('team_distance_covered', 'speed_zones', nullable=False)
    op.alter_column('team_distance_covered', 'game_state', nullable=False)
    op.alter_column('team_distance_covered', 'time_intervals', nullable=False)


def downgrade() -> None:
    """Revert the migration: restore old columns"""
    
    # Step 1: Add back old columns
    op.add_column('team_distance_covered', sa.Column('walking_m', sa.Float(), nullable=True))
    op.add_column('team_distance_covered', sa.Column('jogging_m', sa.Float(), nullable=True))
    op.add_column('team_distance_covered', sa.Column('moderated_intensity_m', sa.Float(), nullable=True))
    op.add_column('team_distance_covered', sa.Column('high_intensity_m', sa.Float(), nullable=True))
    op.add_column('team_distance_covered', sa.Column('sprint_m', sa.Float(), nullable=True))
    op.add_column('team_distance_covered', sa.Column('in_play_m', sa.Float(), nullable=True))
    op.add_column('team_distance_covered', sa.Column('out_of_play_m', sa.Float(), nullable=True))
    op.add_column('team_distance_covered', sa.Column('total_distance_m', sa.Float(), nullable=False))
    
    # Step 2: Migrate data back from JSONB to old columns
    op.execute("""
        UPDATE team_distance_covered
        SET 
            total_distance_m = (metrics->>'total_distance_m')::float,
            walking_m = (speed_zones->>'walking')::float,
            jogging_m = (speed_zones->>'jogging')::float,
            moderated_intensity_m = (speed_zones->>'moderated_intensity')::float,
            high_intensity_m = (speed_zones->>'high_intensity')::float,
            sprint_m = (speed_zones->>'sprint')::float,
            in_play_m = (game_state->>'in_play')::float,
            out_of_play_m = (game_state->>'out_of_play')::float
        WHERE metrics IS NOT NULL OR speed_zones IS NOT NULL OR game_state IS NOT NULL;
    """)
    
    # Step 3: Convert time_intervals from dictionary back to array
    op.execute("""
        UPDATE team_distance_covered
        SET time_intervals = (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'category_name', key,
                    'distance_m', value
                )
            )
            FROM jsonb_each(time_intervals) AS t(key, value)
        )
        WHERE time_intervals IS NOT NULL AND jsonb_typeof(time_intervals) = 'object';
    """)
    
    # Step 4: Drop new JSONB columns
    op.drop_column('team_distance_covered', 'metrics')
    op.drop_column('team_distance_covered', 'speed_zones')
    op.drop_column('team_distance_covered', 'game_state')
