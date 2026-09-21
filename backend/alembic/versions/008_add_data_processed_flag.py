"""Add data_processed flag to games table

Revision ID: 008_add_data_processed_flag
Revises: 007_add_lineups_tables
Create Date: 2026-08-26 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_add_data_processed_flag'
down_revision = '007_add_lineups_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add data_processed column to games table
    op.add_column(
        'games',
        sa.Column('data_processed', sa.Boolean, nullable=False, server_default=sa.false())
    )
    op.create_index('idx_game_data_processed', 'games', ['data_processed'])


def downgrade() -> None:
    op.drop_index('idx_game_data_processed', 'games')
    op.drop_column('games', 'data_processed')
