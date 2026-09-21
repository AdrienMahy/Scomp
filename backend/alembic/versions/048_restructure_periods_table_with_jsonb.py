"""Restructure periods table with JSONB columns (time, direction)

Revision ID: 048
Revises: 047_fix_v_setpieces_detailed_json_structure
Create Date: 2026-09-12

Migration to refactor the periods table:
- Remove old flat columns: start_frame, end_frame, duration, start_time, end_time, 
  home_team_direction, away_team_direction, current_score_home, current_score_away
- Add new JSONB columns:
  * time: { start_frame, end_frame, duration }
  * direction: [ { team: { value: "LTR"/"RTL", coef: 1/-1 } } ]

This enables more flexible storage and cleaner API responses.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '048'
down_revision = '047_fix_v_setpieces_detailed_json_structure'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the migration: add JSONB columns and remove old ones"""
    
    # Step 1: Add new JSONB columns
    op.add_column('periods', sa.Column('time', postgresql.JSON, nullable=True))
    op.add_column('periods', sa.Column('direction', postgresql.JSON, nullable=True))
    
    # Step 2: Migrate data from old columns to new JSONB structure
    # Using raw SQL to handle the data migration
    op.execute("""
        UPDATE periods
        SET 
            time = jsonb_build_object(
                'start_frame', start_frame,
                'end_frame', end_frame,
                'duration', duration
            ),
            direction = jsonb_build_array(
                jsonb_build_object(
                    'team', jsonb_build_object(
                        'value', home_team_direction,
                        'coef', CASE WHEN home_team_direction = 'LTR' THEN 1 ELSE -1 END
                    )
                ),
                jsonb_build_object(
                    'team', jsonb_build_object(
                        'value', away_team_direction,
                        'coef', CASE WHEN away_team_direction = 'LTR' THEN 1 ELSE -1 END
                    )
                )
            )
        WHERE start_frame IS NOT NULL 
           OR end_frame IS NOT NULL 
           OR duration IS NOT NULL
           OR home_team_direction IS NOT NULL
           OR away_team_direction IS NOT NULL;
    """)
    
    # Step 3: Drop old columns
    op.drop_column('periods', 'start_frame')
    op.drop_column('periods', 'end_frame')
    op.drop_column('periods', 'duration')
    op.drop_column('periods', 'start_time')
    op.drop_column('periods', 'end_time')
    op.drop_column('periods', 'home_team_direction')
    op.drop_column('periods', 'away_team_direction')
    op.drop_column('periods', 'current_score_home')
    op.drop_column('periods', 'current_score_away')
    
    # Step 4: Make new columns NOT NULL
    op.alter_column('periods', 'time', nullable=False)
    op.alter_column('periods', 'direction', nullable=False)


def downgrade() -> None:
    """Revert the migration: restore old columns"""
    
    # Step 1: Add back old columns
    op.add_column('periods', sa.Column('start_frame', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('end_frame', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('duration', sa.Float(), nullable=True))
    op.add_column('periods', sa.Column('start_time', sa.Float(), nullable=True))
    op.add_column('periods', sa.Column('end_time', sa.Float(), nullable=True))
    op.add_column('periods', sa.Column('home_team_direction', sa.String(10), nullable=True))
    op.add_column('periods', sa.Column('away_team_direction', sa.String(10), nullable=True))
    op.add_column('periods', sa.Column('current_score_home', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('current_score_away', sa.Integer(), nullable=True))
    
    # Step 2: Migrate data back from JSONB to old columns
    op.execute("""
        UPDATE periods
        SET 
            start_frame = (time->>'start_frame')::INTEGER,
            end_frame = (time->>'end_frame')::INTEGER,
            duration = (time->>'duration')::FLOAT,
            home_team_direction = direction->0->'team'->>'value',
            away_team_direction = direction->1->'team'->>'value'
        WHERE time IS NOT NULL OR direction IS NOT NULL;
    """)
    
    # Step 3: Drop new JSONB columns
    op.drop_column('periods', 'time')
    op.drop_column('periods', 'direction')
