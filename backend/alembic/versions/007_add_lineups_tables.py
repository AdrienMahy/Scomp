"""Add lineup_teams and lineup_players tables

Revision ID: 007_add_lineups_tables
Revises: 006_add_output_files_table
Create Date: 2026-08-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_lineups_tables'
down_revision = '006_add_output_files_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create lineup_teams table
    op.create_table(
        'lineup_teams',
        sa.Column('id', sa.String(200), primary_key=True, nullable=False),
        sa.Column('game_id', sa.String(50), sa.ForeignKey('games.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('team_id', sa.String(50), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('position', sa.String(10), nullable=False),  # 'HOME' or 'AWAY'
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_lineup_team_game', 'lineup_teams', ['game_id'])
    op.create_index('idx_lineup_team_team', 'lineup_teams', ['team_id'])

    # Create lineup_players table
    op.create_table(
        'lineup_players',
        sa.Column('id', sa.String(200), primary_key=True, nullable=False),
        sa.Column('lineup_team_id', sa.String(200), sa.ForeignKey('lineup_teams.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('player_id', sa.String(50), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('position', sa.String(50), nullable=True),
        sa.Column('shirt_number', sa.Integer, nullable=True),
        sa.Column('starting', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_lineup_player_lineup', 'lineup_players', ['lineup_team_id'])
    op.create_index('idx_lineup_player_player', 'lineup_players', ['player_id'])


def downgrade() -> None:
    op.drop_index('idx_lineup_player_player', 'lineup_players')
    op.drop_index('idx_lineup_player_lineup', 'lineup_players')
    op.drop_table('lineup_players')
    op.drop_index('idx_lineup_team_team', 'lineup_teams')
    op.drop_index('idx_lineup_team_game', 'lineup_teams')
    op.drop_table('lineup_teams')
