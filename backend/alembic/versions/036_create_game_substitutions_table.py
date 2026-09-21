"""Create game_substitutions table

Revision ID: 036_create_game_substitutions_table
Revises: 035_drop_game_goals_game_cards_tables
Create Date: 2026-09-09 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '036_create_game_substitutions_table'
down_revision = '035_drop_game_goals_game_cards_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column('timestamp', sa.Float(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['player_in_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['player_out_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for foreign keys
    op.create_index('ix_game_substitutions_game_id', 'game_substitutions', ['game_id'])
    op.create_index('ix_game_substitutions_player_in_id', 'game_substitutions', ['player_in_id'])
    op.create_index('ix_game_substitutions_player_out_id', 'game_substitutions', ['player_out_id'])
    op.create_index('ix_game_substitutions_team_id', 'game_substitutions', ['team_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_game_substitutions_team_id', table_name='game_substitutions')
    op.drop_index('ix_game_substitutions_player_out_id', table_name='game_substitutions')
    op.drop_index('ix_game_substitutions_player_in_id', table_name='game_substitutions')
    op.drop_index('ix_game_substitutions_game_id', table_name='game_substitutions')
    
    # Drop table
    op.drop_table('game_substitutions')
