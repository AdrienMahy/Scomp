"""Fix UUID foreign key type mismatches in fitness tables

Revision ID: 037_fix_fitness_entities_fk_types
Revises: 036_create_game_substitutions_table
Create Date: 2026-09-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '037_fix_fitness_entities_fk_types'
down_revision = '036_create_game_substitutions_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix player_fitness_runs table FK type mismatches
    op.alter_column(
        'player_fitness_runs',
        'player_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=False,
    )
    op.alter_column(
        'player_fitness_runs',
        'team_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=False,
    )
    op.alter_column(
        'player_fitness_runs',
        'opponent_team_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=False,
    )
    
    # Fix event reference FK types in player_fitness_runs
    op.alter_column(
        'player_fitness_runs',
        'possession_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=True,
    )
    op.alter_column(
        'player_fitness_runs',
        'phase_of_play_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=True,
    )
    op.alter_column(
        'player_fitness_runs',
        'type_of_play_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=True,
    )
    op.alter_column(
        'player_fitness_runs',
        'individual_possession_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=True,
    )
    
    # Fix player_fitness_summary table FK types
    op.alter_column(
        'player_fitness_summary',
        'player_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=False,
    )
    op.alter_column(
        'player_fitness_summary',
        'team_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=False,
    )
    
    # Fix team_fitness_summary table FK type
    op.alter_column(
        'team_fitness_summary',
        'team_id',
        existing_type=sa.UUID(),
        type_=sa.String(50),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Revert player_fitness_runs to UUID types
    op.alter_column(
        'player_fitness_runs',
        'player_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=False,
    )
    op.alter_column(
        'player_fitness_runs',
        'team_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=False,
    )
    op.alter_column(
        'player_fitness_runs',
        'opponent_team_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=False,
    )
    op.alter_column(
        'player_fitness_runs',
        'possession_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=True,
    )
    op.alter_column(
        'player_fitness_runs',
        'phase_of_play_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=True,
    )
    op.alter_column(
        'player_fitness_runs',
        'type_of_play_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=True,
    )
    op.alter_column(
        'player_fitness_runs',
        'individual_possession_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=True,
    )
    op.alter_column(
        'player_fitness_summary',
        'player_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=False,
    )
    op.alter_column(
        'player_fitness_summary',
        'team_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=False,
    )
    op.alter_column(
        'team_fitness_summary',
        'team_id',
        existing_type=sa.String(50),
        type_=sa.UUID(),
        existing_nullable=False,
    )
