"""Add competitions and seasons tables

Revision ID: 003_add_competitions_and_seasons
Revises: 002_add_fitness_entities
Create Date: 2026-08-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_competitions_and_seasons'
down_revision = '002_add_fitness_entities'
branch_labels = None
depends_on = None


def upgrade():
    """Add competitions and seasons tables"""
    
    # ========================================================================
    # COMPETITIONS TABLE
    # ========================================================================
    op.create_table(
        'competitions',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'provider', name='uq_competition_name_provider'),
    )
    op.create_index('idx_competitions_name', 'competitions', ['name'])
    op.create_index('idx_competitions_provider', 'competitions', ['provider'])
    
    # ========================================================================
    # SEASONS TABLE
    # ========================================================================
    op.create_table(
        'seasons',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('competition_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('season_year', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('competition_id', 'name', name='uq_season_competition_name'),
    )
    op.create_index('idx_seasons_competition', 'seasons', ['competition_id'])
    op.create_index('idx_seasons_name', 'seasons', ['name'])
    op.create_index('idx_seasons_year', 'seasons', ['season_year'])
    
    # ========================================================================
    # ADD FOREIGN KEYS TO GAMES TABLE (columns already exist from migration 000)
    # ========================================================================
    # Just add the foreign key constraints, columns already exist
    op.create_foreign_key(
        'fk_games_competition_id',
        'games',
        'competitions',
        ['competition_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_games_season_id',
        'games',
        'seasons',
        ['season_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_index('idx_games_competition', 'games', ['competition_id'])
    op.create_index('idx_games_season', 'games', ['season_id'])


def downgrade():
    """Downgrade - remove competitions and seasons tables"""
    
    # Drop indices
    op.drop_index('idx_games_season', 'games')
    op.drop_index('idx_games_competition', 'games')
    
    # Drop foreign keys
    op.drop_constraint('fk_games_season_id', 'games', type_='foreignkey')
    op.drop_constraint('fk_games_competition_id', 'games', type_='foreignkey')
    
    # Drop indices
    op.drop_index('idx_seasons_year', 'seasons')
    op.drop_index('idx_seasons_name', 'seasons')
    op.drop_index('idx_seasons_competition', 'seasons')
    
    # Drop tables
    op.drop_table('seasons')
    op.drop_table('competitions')
