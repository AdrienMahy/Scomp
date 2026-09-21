"""Add round column to scraping_logs table for round info in logs.

Revision ID: 030_add_round_to_scraping_logs
Revises: 029_create_game_data_summary_view
Create Date: 2026-09-08 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '030_add_round_to_scraping_logs'
down_revision = '029_create_game_data_summary_view'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add round column to scraping_logs table
    op.add_column(
        'scraping_logs',
        sa.Column('round', sa.String(20), nullable=True)
    )


def downgrade() -> None:
    # Remove round column
    op.drop_column('scraping_logs', 'round')
