"""Add game_goals and game_cards tables for event persistence

Revision ID: 015_event_tables
Revises: 014_cleanup_periods_schema
Create Date: 2026-08-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015_event_tables'
down_revision = '014_cleanup_periods_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Create game_goals and game_cards tables"""
    
    # ========================================================================
    # game_goals TABLE
    # ========================================================================
    op.create_table(
        'game_goals',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('player_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('period', sa.Integer(), nullable=False),
        sa.Column('frame', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=True),
        sa.Column('own_goal', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_game_goals_game_id'), 'game_goals', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_goals_player_id'), 'game_goals', ['player_id'], unique=False)
    op.create_index(op.f('ix_game_goals_team_id'), 'game_goals', ['team_id'], unique=False)
    
    # ========================================================================
    # game_cards TABLE
    # ========================================================================
    op.create_table(
        'game_cards',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('player_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('period', sa.Integer(), nullable=False),
        sa.Column('frame', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=True),
        sa.Column('card_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_game_cards_game_id'), 'game_cards', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_cards_player_id'), 'game_cards', ['player_id'], unique=False)
    op.create_index(op.f('ix_game_cards_team_id'), 'game_cards', ['team_id'], unique=False)


def downgrade():
    """Drop game_cards and game_goals tables"""
    op.drop_index(op.f('ix_game_cards_team_id'), table_name='game_cards')
    op.drop_index(op.f('ix_game_cards_player_id'), table_name='game_cards')
    op.drop_index(op.f('ix_game_cards_game_id'), table_name='game_cards')
    op.drop_table('game_cards')
    
    op.drop_index(op.f('ix_game_goals_team_id'), table_name='game_goals')
    op.drop_index(op.f('ix_game_goals_player_id'), table_name='game_goals')
    op.drop_index(op.f('ix_game_goals_game_id'), table_name='game_goals')
    op.drop_table('game_goals')
