"""Refactor distance_covered to Option 2: denormalized speed zones + time intervals table

Revision ID: h9j0k1l2m3n4
Revises: f7h8i9j0k1l2
Create Date: 2026-08-18 14:36:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'h9j0k1l2m3n4'
down_revision = 'f7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade: Refactor team_distance_covered table
    - Remove: breakdowns JSONB column
    - Add: walking_m, jogging_m, moderated_intensity_m, high_intensity_m, sprint_m columns
    - Create: team_distance_breakdowns table for time intervals (if not exists)
    """
    
    # Drop breakdowns column from team_distance_covered (if it exists)
    try:
        op.drop_column('team_distance_covered', 'breakdowns')
    except:
        pass  # Column may not exist
    
    # Add speed zone columns to team_distance_covered (if not exist)
    try:
        op.add_column('team_distance_covered', sa.Column('walking_m', sa.Float(), nullable=True))
    except:
        pass
    
    try:
        op.add_column('team_distance_covered', sa.Column('jogging_m', sa.Float(), nullable=True))
    except:
        pass
    
    try:
        op.add_column('team_distance_covered', sa.Column('moderated_intensity_m', sa.Float(), nullable=True))
    except:
        pass
    
    try:
        op.add_column('team_distance_covered', sa.Column('high_intensity_m', sa.Float(), nullable=True))
    except:
        pass
    
    try:
        op.add_column('team_distance_covered', sa.Column('sprint_m', sa.Float(), nullable=True))
    except:
        pass
    
    # Create team_distance_breakdowns table (if not exists) - handle with raw SQL
    # since op.create_table doesn't support IF NOT EXISTS
    from sqlalchemy import text
    from sqlalchemy.engine import Connection
    
    conn = op.get_bind()
    
    # Check if table exists
    inspector = sa.inspect(conn)
    if 'team_distance_breakdowns' not in inspector.get_table_names():
        op.create_table(
            'team_distance_breakdowns',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('game_id', sa.String(36), nullable=False),
            sa.Column('team_id', sa.String(36), nullable=False),
            sa.Column('team_distance_id', sa.String(36), nullable=False),
            sa.Column('category_type', sa.String(50), nullable=False),
            sa.Column('category_name', sa.String(100), nullable=False),
            sa.Column('distance_m', sa.Float(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['team_distance_id'], ['team_distance_covered.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        
        # Create indices for queryability
        op.create_index('ix_team_distance_breakdowns_game_id', 'team_distance_breakdowns', ['game_id'])
        op.create_index('ix_team_distance_breakdowns_team_id', 'team_distance_breakdowns', ['team_id'])
        op.create_index('ix_team_distance_breakdowns_team_distance_id', 'team_distance_breakdowns', ['team_distance_id'])
        op.create_index('ix_team_distance_breakdowns_category', 'team_distance_breakdowns', ['category_type', 'category_name'])


def downgrade() -> None:
    """
    Downgrade: Restore original team_distance_covered structure
    - Drop: team_distance_breakdowns table
    - Remove: speed zone columns
    - Restore: breakdowns JSONB column
    """
    
    # Drop team_distance_breakdowns table
    op.drop_index('ix_team_distance_breakdowns_category', table_name='team_distance_breakdowns')
    op.drop_index('ix_team_distance_breakdowns_team_distance_id', table_name='team_distance_breakdowns')
    op.drop_index('ix_team_distance_breakdowns_team_id', table_name='team_distance_breakdowns')
    op.drop_index('ix_team_distance_breakdowns_game_id', table_name='team_distance_breakdowns')
    op.drop_table('team_distance_breakdowns')
    
    # Drop speed zone columns
    op.drop_column('team_distance_covered', 'sprint_m')
    op.drop_column('team_distance_covered', 'high_intensity_m')
    op.drop_column('team_distance_covered', 'moderated_intensity_m')
    op.drop_column('team_distance_covered', 'jogging_m')
    op.drop_column('team_distance_covered', 'walking_m')
    
    # Restore breakdowns column
    op.add_column('team_distance_covered', sa.Column('breakdowns', postgresql.JSON(), nullable=True))
