"""Recreate lineup_players table with integer primary key

Revision ID: 8f3ea1c212aa
Revises: 42254d1db2f8
Create Date: 2026-08-14 15:05:33.763126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f3ea1c212aa'
down_revision: Union[str, None] = '42254d1db2f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create lineup_players table with integer primary key
    op.create_table(
        'lineup_players',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('lineup_team_id', sa.String(length=200), nullable=False),
        sa.Column('player_id', sa.String(length=50), nullable=False),
        sa.Column('is_starting', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('is_captain', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('formation_field', sa.String(length=50), nullable=True),
        sa.Column('formation_position', sa.Integer(), nullable=True),
        sa.Column('jersey_number', sa.Integer(), nullable=True),
        sa.Column('playing_time', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['lineup_team_id'], ['lineup_teams.id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lineup_players_lineup_team_id'), 'lineup_players', ['lineup_team_id'], unique=False)
    op.create_index(op.f('ix_lineup_players_player_id'), 'lineup_players', ['player_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lineup_players_player_id'), table_name='lineup_players')
    op.drop_index(op.f('ix_lineup_players_lineup_team_id'), table_name='lineup_players')
    op.drop_table('lineup_players')
