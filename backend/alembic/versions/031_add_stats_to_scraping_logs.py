"""Add stats JSONB column to scraping_logs for table-level DELETE/INSERT tracking

Revision ID: 031_add_stats_to_scraping_logs
Revises: 030_add_round_to_scraping_logs
Create Date: 2026-09-08 13:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '031_add_stats_to_scraping_logs'
down_revision = '030_add_round_to_scraping_logs'
branch_labels = None
depends_on = None


def upgrade():
    # Add stats column to scraping_logs
    op.add_column(
        'scraping_logs',
        sa.Column('stats', postgresql.JSON, nullable=True, comment='Table-level DELETE/INSERT counts: {"table_name": {"deleted": 0, "inserted": 10}}')
    )


def downgrade():
    # Remove stats column
    op.drop_column('scraping_logs', 'stats')
