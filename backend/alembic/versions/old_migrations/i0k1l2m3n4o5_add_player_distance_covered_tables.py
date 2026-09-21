"""Add player distance covered tables

Revision ID: i0k1l2m3n4o5
Revises: h9j0k1l2m3n4
Create Date: 2026-08-18 14:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'i0k1l2m3n4o5'
down_revision = 'h9j0k1l2m3n4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade: Create player distance tables
    - Create: player_distance_covered table with denormalized speed zones
    - Create: player_distance_breakdowns table for time intervals
    """
    
    # Create player_distance_covered table
    op.create_table(
        'player_distance_covered',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('game_id', sa.String(36), nullable=False),
        sa.Column('player_id', sa.String(36), nullable=False),
        sa.Column('minutes_played', sa.Float(), nullable=True),
        sa.Column('total_distance_m', sa.Float(), nullable=False),
        sa.Column('distance_per_min_played_m', sa.Float(), nullable=True),
        sa.Column('walking_m', sa.Float(), nullable=True),
        sa.Column('jogging_m', sa.Float(), nullable=True),
        sa.Column('moderated_intensity_m', sa.Float(), nullable=True),
        sa.Column('high_intensity_m', sa.Float(), nullable=True),
        sa.Column('sprint_m', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indices for player_distance_covered
    op.create_index('ix_player_distance_covered_game_id', 'player_distance_covered', ['game_id'])
    op.create_index('ix_player_distance_covered_player_id', 'player_distance_covered', ['player_id'])
    
    # Create player_distance_breakdowns table
    op.create_table(
        'player_distance_breakdowns',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('game_id', sa.String(36), nullable=False),
        sa.Column('player_id', sa.String(36), nullable=False),
        sa.Column('player_distance_id', sa.String(36), nullable=False),
        sa.Column('category_type', sa.String(50), nullable=False),
        sa.Column('category_name', sa.String(100), nullable=False),
        sa.Column('distance_m', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_distance_id'], ['player_distance_covered.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indices for player_distance_breakdowns
    op.create_index('ix_player_distance_breakdowns_game_id', 'player_distance_breakdowns', ['game_id'])
    op.create_index('ix_player_distance_breakdowns_player_id', 'player_distance_breakdowns', ['player_id'])
    op.create_index('ix_player_distance_breakdowns_player_distance_id', 'player_distance_breakdowns', ['player_distance_id'])
    op.create_index('ix_player_distance_breakdowns_category', 'player_distance_breakdowns', ['category_type', 'category_name'])


def downgrade() -> None:
    """
    Downgrade: Drop player distance tables
    """
    
    # Drop player_distance_breakdowns table
    op.drop_index('ix_player_distance_breakdowns_category', table_name='player_distance_breakdowns')
    op.drop_index('ix_player_distance_breakdowns_player_distance_id', table_name='player_distance_breakdowns')
    op.drop_index('ix_player_distance_breakdowns_player_id', table_name='player_distance_breakdowns')
    op.drop_index('ix_player_distance_breakdowns_game_id', table_name='player_distance_breakdowns')
    op.drop_table('player_distance_breakdowns')
    
    # Drop player_distance_covered table
    op.drop_index('ix_player_distance_covered_player_id', table_name='player_distance_covered')
    op.drop_index('ix_player_distance_covered_game_id', table_name='player_distance_covered')
    op.drop_table('player_distance_covered')
