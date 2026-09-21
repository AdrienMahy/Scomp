"""Add metadata tables (goals, subs, cards, score_evolution) and enrich periods

Revision ID: d5be0573c3ee
Revises: f5g6h7i8j9k0
Create Date: 2026-08-18 14:13:22.850470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5be0573c3ee'
down_revision: Union[str, None] = 'f5g6h7i8j9k0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create game_goals table
    op.create_table(
        'game_goals',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('player_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('period', sa.Integer(), nullable=False),
        sa.Column('frame', sa.Integer(), nullable=False),
        sa.Column('own_goal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_game_goals_game_id'), 'game_goals', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_goals_player_id'), 'game_goals', ['player_id'], unique=False)
    op.create_index(op.f('ix_game_goals_team_id'), 'game_goals', ['team_id'], unique=False)

    # Create game_substitutions table
    op.create_table(
        'game_substitutions',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('player_in_id', sa.String(50), nullable=False),
        sa.Column('player_out_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('period', sa.Integer(), nullable=False),
        sa.Column('frame', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['player_in_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['player_out_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_game_substitutions_game_id'), 'game_substitutions', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_substitutions_player_in_id'), 'game_substitutions', ['player_in_id'], unique=False)
    op.create_index(op.f('ix_game_substitutions_player_out_id'), 'game_substitutions', ['player_out_id'], unique=False)
    op.create_index(op.f('ix_game_substitutions_team_id'), 'game_substitutions', ['team_id'], unique=False)

    # Create game_cards table
    op.create_table(
        'game_cards',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('player_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('period', sa.Integer(), nullable=False),
        sa.Column('frame', sa.Integer(), nullable=False),
        sa.Column('card_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_game_cards_game_id'), 'game_cards', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_cards_player_id'), 'game_cards', ['player_id'], unique=False)
    op.create_index(op.f('ix_game_cards_team_id'), 'game_cards', ['team_id'], unique=False)
    op.create_index(op.f('ix_game_cards_card_type'), 'game_cards', ['card_type'], unique=False)

    # Create game_score_evolution table
    op.create_table(
        'game_score_evolution',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('period_id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('score', sa.String(20), nullable=False),
        sa.Column('score_home', sa.Integer(), nullable=False),
        sa.Column('score_away', sa.Integer(), nullable=False),
        sa.Column('frame_start', sa.Integer(), nullable=False),
        sa.Column('frame_end', sa.Integer(), nullable=False),
        sa.Column('timestamp_start', sa.Float(), nullable=False),
        sa.Column('timestamp_end', sa.Float(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['period_id'], ['periods.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_game_score_evolution_game_id'), 'game_score_evolution', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_score_evolution_period_id'), 'game_score_evolution', ['period_id'], unique=False)
    op.create_index(op.f('ix_game_score_evolution_score'), 'game_score_evolution', ['score'], unique=False)

    # Add columns to periods table
    op.add_column('periods', sa.Column('start_frame', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('end_frame', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('duration', sa.Float(), nullable=True))
    op.add_column('periods', sa.Column('home_team_direction', sa.String(10), nullable=True))
    op.add_column('periods', sa.Column('away_team_direction', sa.String(10), nullable=True))
    op.add_column('periods', sa.Column('current_score_home', sa.Integer(), nullable=True))
    op.add_column('periods', sa.Column('current_score_away', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove columns from periods table
    op.drop_column('periods', 'current_score_away')
    op.drop_column('periods', 'current_score_home')
    op.drop_column('periods', 'away_team_direction')
    op.drop_column('periods', 'home_team_direction')
    op.drop_column('periods', 'duration')
    op.drop_column('periods', 'end_frame')
    op.drop_column('periods', 'start_frame')

    # Drop game_score_evolution table
    op.drop_index(op.f('ix_game_score_evolution_score'), table_name='game_score_evolution')
    op.drop_index(op.f('ix_game_score_evolution_period_id'), table_name='game_score_evolution')
    op.drop_index(op.f('ix_game_score_evolution_game_id'), table_name='game_score_evolution')
    op.drop_table('game_score_evolution')

    # Drop game_cards table
    op.drop_index(op.f('ix_game_cards_card_type'), table_name='game_cards')
    op.drop_index(op.f('ix_game_cards_team_id'), table_name='game_cards')
    op.drop_index(op.f('ix_game_cards_player_id'), table_name='game_cards')
    op.drop_index(op.f('ix_game_cards_game_id'), table_name='game_cards')
    op.drop_table('game_cards')

    # Drop game_substitutions table
    op.drop_index(op.f('ix_game_substitutions_team_id'), table_name='game_substitutions')
    op.drop_index(op.f('ix_game_substitutions_player_out_id'), table_name='game_substitutions')
    op.drop_index(op.f('ix_game_substitutions_player_in_id'), table_name='game_substitutions')
    op.drop_index(op.f('ix_game_substitutions_game_id'), table_name='game_substitutions')
    op.drop_table('game_substitutions')

    # Drop game_goals table
    op.drop_index(op.f('ix_game_goals_team_id'), table_name='game_goals')
    op.drop_index(op.f('ix_game_goals_player_id'), table_name='game_goals')
    op.drop_index(op.f('ix_game_goals_game_id'), table_name='game_goals')
    op.drop_table('game_goals')
