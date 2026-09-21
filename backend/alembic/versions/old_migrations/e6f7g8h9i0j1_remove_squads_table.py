"""Remove squads table - replaced by metadata.json lineups

Revision ID: e6f7g8h9i0j1
Revises: d5be0573c3ee
Create Date: 2026-08-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6f7g8h9i0j1'
down_revision = 'd5be0573c3ee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop foreign key constraint first
    op.drop_constraint('squads_game_id_fkey', 'squads', type_='foreignkey')
    op.drop_constraint('squads_team_id_fkey', 'squads', type_='foreignkey')
    
    # Drop index
    op.drop_index('ix_squads_game_id', table_name='squads')
    op.drop_index('ix_squads_team_id', table_name='squads')
    
    # Drop table
    op.drop_table('squads')


def downgrade() -> None:
    # Recreate table
    op.create_table(
        'squads',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('team_id', sa.String(50), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], name='squads_game_id_fkey'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], name='squads_team_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='squads_pkey'),
    )
    
    # Recreate indices
    op.create_index('ix_squads_game_id', 'squads', ['game_id'])
    op.create_index('ix_squads_team_id', 'squads', ['team_id'])
