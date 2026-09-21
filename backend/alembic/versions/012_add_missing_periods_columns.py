"""Add missing columns to periods table

Revision ID: 012_add_missing_periods_columns
Revises: 011_add_game_score_evolution
Create Date: 2026-08-27 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012_add_missing_periods_columns'
down_revision = '011_add_game_score_evolution'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to periods table
    # These columns are defined in the Period model but missing from the schema
    
    # Add period_id (period number: 1, 2, 3)
    op.add_column('periods', sa.Column('period_id', sa.Integer(), nullable=True))
    
    # Add video frame information
    op.add_column('periods', sa.Column('start_frame', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('end_frame', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('duration', sa.Float(), nullable=True))
    
    # Add timing (legacy, prefer frames)
    op.add_column('periods', sa.Column('start_time', sa.Float(), nullable=True))
    op.add_column('periods', sa.Column('end_time', sa.Float(), nullable=True))
    
    # Add team directions on pitch
    op.add_column('periods', sa.Column('home_team_direction', sa.String(10), nullable=True))
    op.add_column('periods', sa.Column('away_team_direction', sa.String(10), nullable=True))
    
    # Add score at end of period
    op.add_column('periods', sa.Column('current_score_home', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('current_score_away', sa.Integer(), nullable=True))


def downgrade():
    # Remove columns in reverse order
    op.drop_column('periods', 'current_score_away')
    op.drop_column('periods', 'current_score_home')
    op.drop_column('periods', 'away_team_direction')
    op.drop_column('periods', 'home_team_direction')
    op.drop_column('periods', 'end_time')
    op.drop_column('periods', 'start_time')
    op.drop_column('periods', 'duration')
    op.drop_column('periods', 'end_frame')
    op.drop_column('periods', 'start_frame')
    op.drop_column('periods', 'period_id')
