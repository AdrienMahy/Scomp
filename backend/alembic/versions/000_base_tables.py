"""Create base tables for games, teams, players

Revision ID: 000_base_tables
Revises:
Create Date: 2026-08-25 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '000_base_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create games table
    op.create_table(
        'games',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('competition_id', sa.String(50), nullable=True, index=True),
        sa.Column('season_id', sa.String(50), nullable=True, index=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('round', sa.String(50), nullable=True),
        sa.Column('starts_at', sa.DateTime, nullable=True),
        sa.Column('played_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_game_competition', 'games', ['competition_id'])
    op.create_index('idx_game_season', 'games', ['season_id'])

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('competition_id', sa.String(50), nullable=True, index=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('brand', sa.String(255), nullable=True),
        sa.Column('providers', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create players table
    op.create_table(
        'players',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('usage_name', sa.String(200), nullable=True),
        sa.Column('photo', sa.String(500), nullable=True),
        sa.Column('age', sa.Integer, nullable=True),
        sa.Column('birthdate', sa.Date, nullable=True),
        sa.Column('current_team_id', sa.String(50), nullable=True),
        sa.Column('current_team_brand', sa.String(255), nullable=True),
        sa.Column('current_national_team_id', sa.String(50), nullable=True),
        sa.Column('current_national_team_brand', sa.String(255), nullable=True),
        sa.Column('nationalities', sa.JSON, nullable=True),
        sa.Column('positions', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create periods table (referenced by events)
    op.create_table(
        'periods',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('game_id', sa.String(50), sa.ForeignKey('games.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_number', sa.Integer, nullable=False),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_period_game', 'periods', ['game_id'])


def downgrade() -> None:
    op.drop_index('idx_period_game', 'periods')
    op.drop_table('periods')
    op.drop_index('idx_game_season', 'games')
    op.drop_index('idx_game_competition', 'games')
    op.drop_table('players')
    op.drop_table('teams')
    op.drop_table('games')
