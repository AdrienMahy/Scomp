"""Create RGD tables - Ball In Play, Possession, Type of Play, Phase of Play

Revision ID: rgd_001_create_hierarchy
Revises: j5k6l7m8n9o0
Create Date: 2026-08-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'rgd_001_create_hierarchy'
down_revision: Union[str, None] = 'j5k6l7m8n9o0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create BALL_IN_PLAY table
    op.create_table(
        'ball_in_play',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('game_id', sa.String(length=50), nullable=False),
        sa.Column('sequence_id', sa.UUID(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('start_frame', sa.Integer(), nullable=False),
        sa.Column('end_frame', sa.Integer(), nullable=False),
        sa.Column('outcome', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('start_frame < end_frame', name='check_bip_frames_order'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sequence_id')
    )
    op.create_index('idx_bip_game_id', 'ball_in_play', ['game_id'])
    op.create_index('idx_bip_period', 'ball_in_play', ['period_id'])
    op.create_index('idx_bip_frames', 'ball_in_play', ['start_frame', 'end_frame'])

    # Create POSSESSION_COLLECTIVE table
    op.create_table(
        'possession_collective',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('game_id', sa.String(length=50), nullable=False),
        sa.Column('ball_in_play_id', sa.UUID(), nullable=False),
        sa.Column('team_id', sa.String(length=50), nullable=False),
        sa.Column('opponent_team_id', sa.String(length=50), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('start_frame', sa.Integer(), nullable=False),
        sa.Column('end_frame', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('n_events', sa.Integer(), nullable=True),
        sa.Column('n_passes', sa.Integer(), nullable=True),
        sa.Column('n_passes_category', sa.String(length=255), nullable=True),
        sa.Column('distance_gained', sa.Float(), nullable=True),
        sa.Column('distance_gained_pct', sa.Float(), nullable=True),
        sa.Column('possession_outcome', sa.String(length=50), nullable=True),
        sa.Column('goal_in_sequence', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('shot_in_sequence', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('formation', sa.String(length=20), nullable=True),
        sa.Column('attacking_style', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('start_frame < end_frame', name='check_pc_frames_order'),
        sa.ForeignKeyConstraint(['ball_in_play_id'], ['ball_in_play.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opponent_team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pc_game_id', 'possession_collective', ['game_id'])
    op.create_index('idx_pc_bip_id', 'possession_collective', ['ball_in_play_id'])
    op.create_index('idx_pc_team_id', 'possession_collective', ['team_id'])
    op.create_index('idx_pc_period', 'possession_collective', ['period_id'])

    # Create TYPES_OF_PLAY table
    op.create_table(
        'types_of_play',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('game_id', sa.String(length=50), nullable=False),
        sa.Column('possession_collective_id', sa.UUID(), nullable=False),
        sa.Column('team_id', sa.String(length=50), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('play_type', sa.String(length=50), nullable=False),
        sa.Column('start_frame', sa.Integer(), nullable=False),
        sa.Column('end_frame', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('n_events', sa.Integer(), nullable=True),
        sa.Column('n_passes', sa.Integer(), nullable=True),
        sa.Column('distance_gained', sa.Float(), nullable=True),
        sa.Column('sequence_xg', sa.Float(), nullable=True),
        sa.Column('outcome', sa.String(length=50), nullable=True),
        sa.Column('goal_in_sequence', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('shot_in_sequence', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('start_frame < end_frame', name='check_top_frames_order'),
        sa.CheckConstraint(
            "play_type IN ('STRUCTURED_PLAY', 'FAST_PLAY', 'COUNTER_ATTACK')",
            name='check_valid_play_type'
        ),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['possession_collective_id'], ['possession_collective.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_top_game_id', 'types_of_play', ['game_id'])
    op.create_index('idx_top_possession_id', 'types_of_play', ['possession_collective_id'])
    op.create_index('idx_top_play_type', 'types_of_play', ['play_type'])

    # Create PHASES_OF_PLAY table
    op.create_table(
        'phases_of_play',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('game_id', sa.String(length=50), nullable=False),
        sa.Column('type_of_play_id', sa.UUID(), nullable=False),
        sa.Column('possession_collective_id', sa.UUID(), nullable=True),
        sa.Column('team_id', sa.String(length=50), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('phase_type', sa.String(length=100), nullable=False),
        sa.Column('phase_label', sa.String(length=255), nullable=True),
        sa.Column('defensive_block_type', sa.String(length=20), nullable=True),
        sa.Column('defensive_block_area', sa.String(length=50), nullable=True),
        sa.Column('defensive_block_depth', sa.Float(), nullable=True),
        sa.Column('start_frame', sa.Integer(), nullable=False),
        sa.Column('end_frame', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('outcome', sa.String(length=50), nullable=True),
        sa.Column('goal_in_sequence', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('shot_in_sequence', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('start_frame < end_frame', name='check_pop_frames_order'),
        sa.CheckConstraint(
            "phase_type IN ('ATTACK_VS_MID_BLOCK', 'ATTACK_VS_HIGH_BLOCK', 'ATTACK_VS_LOW_BLOCK', 'ATTACK_VS_INDIVIDUAL', 'DEFENSIVE', 'TRANSITION')",
            name='check_valid_phase_type'
        ),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['possession_collective_id'], ['possession_collective.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['type_of_play_id'], ['types_of_play.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pop_game_id', 'phases_of_play', ['game_id'])
    op.create_index('idx_pop_type_id', 'phases_of_play', ['type_of_play_id'])
    op.create_index('idx_pop_possession_id', 'phases_of_play', ['possession_collective_id'])
    op.create_index('idx_pop_phase_type', 'phases_of_play', ['phase_type'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_pop_phase_type', table_name='phases_of_play')
    op.drop_index('idx_pop_possession_id', table_name='phases_of_play')
    op.drop_index('idx_pop_type_id', table_name='phases_of_play')
    op.drop_index('idx_pop_game_id', table_name='phases_of_play')
    op.drop_index('idx_top_play_type', table_name='types_of_play')
    op.drop_index('idx_top_possession_id', table_name='types_of_play')
    op.drop_index('idx_top_game_id', table_name='types_of_play')
    op.drop_index('idx_pc_period', table_name='possession_collective')
    op.drop_index('idx_pc_team_id', table_name='possession_collective')
    op.drop_index('idx_pc_bip_id', table_name='possession_collective')
    op.drop_index('idx_pc_game_id', table_name='possession_collective')
    op.drop_index('idx_bip_frames', table_name='ball_in_play')
    op.drop_index('idx_bip_period', table_name='ball_in_play')
    op.drop_index('idx_bip_game_id', table_name='ball_in_play')

    # Drop tables (in reverse order of creation)
    op.drop_table('phases_of_play')
    op.drop_table('types_of_play')
    op.drop_table('possession_collective')
    op.drop_table('ball_in_play')
