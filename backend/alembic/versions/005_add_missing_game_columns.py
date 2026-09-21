"""Add missing columns to games table

Revision ID: 005_add_missing_game_columns
Revises: 004_add_game_status
Create Date: 2026-08-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_missing_game_columns'
down_revision = '004_add_game_status'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to games table"""
    
    # Add home/away team IDs (foreign keys)
    op.add_column('games', sa.Column('home_team_id', sa.String(50), nullable=True))
    op.add_column('games', sa.Column('away_team_id', sa.String(50), nullable=True))
    
    # Add result column
    op.add_column('games', sa.Column('result', sa.String(20), nullable=True))
    
    # Add score columns
    op.add_column('games', sa.Column('home_score', sa.Integer(), nullable=True))
    op.add_column('games', sa.Column('away_score', sa.Integer(), nullable=True))
    
    # Add formation columns
    op.add_column('games', sa.Column('home_team_formation', sa.String(50), nullable=True))
    op.add_column('games', sa.Column('away_team_formation', sa.String(50), nullable=True))
    
    # Add raw_data column
    op.add_column('games', sa.Column('raw_data', sa.JSON(), nullable=True))
    
    # Add rename column: round -> round_name (we'll keep both for now)
    op.add_column('games', sa.Column('round_name', sa.String(100), nullable=True))
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_games_home_team_id',
        'games',
        'teams',
        ['home_team_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_games_away_team_id',
        'games',
        'teams',
        ['away_team_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create indices
    op.create_index('idx_games_result', 'games', ['result'])
    op.create_index('idx_games_home_team', 'games', ['home_team_id'])
    op.create_index('idx_games_away_team', 'games', ['away_team_id'])
    op.create_index('idx_games_round_name', 'games', ['round_name'])


def downgrade():
    """Remove missing columns from games table"""
    
    # Drop indices
    op.drop_index('idx_games_round_name', 'games')
    op.drop_index('idx_games_away_team', 'games')
    op.drop_index('idx_games_home_team', 'games')
    op.drop_index('idx_games_result', 'games')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_games_away_team_id', 'games', type_='foreignkey')
    op.drop_constraint('fk_games_home_team_id', 'games', type_='foreignkey')
    
    # Drop columns
    op.drop_column('games', 'round_name')
    op.drop_column('games', 'raw_data')
    op.drop_column('games', 'away_team_formation')
    op.drop_column('games', 'home_team_formation')
    op.drop_column('games', 'away_score')
    op.drop_column('games', 'home_score')
    op.drop_column('games', 'result')
    op.drop_column('games', 'away_team_id')
    op.drop_column('games', 'home_team_id')
