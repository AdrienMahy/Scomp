"""Add substitute, playing_time, and individual_possession to lineup_players

Revision ID: 033_add_lineup_player_fields
Revises: 032_add_distance_covered_tables
Create Date: 2026-09-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '033_add_lineup_player_fields'
down_revision = '032_add_distance_covered_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to lineup_players table
    op.add_column('lineup_players', sa.Column('is_substitute', sa.Boolean, nullable=True, server_default=sa.false()))
    op.add_column('lineup_players', sa.Column('playing_time', sa.Float, nullable=True))
    op.add_column('lineup_players', sa.Column('individual_possession', sa.Float, nullable=True))


def downgrade() -> None:
    op.drop_column('lineup_players', 'individual_possession')
    op.drop_column('lineup_players', 'playing_time')
    op.drop_column('lineup_players', 'is_substitute')
