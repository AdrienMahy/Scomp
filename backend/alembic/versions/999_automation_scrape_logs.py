"""Create automation_scrape_logs table

Revision ID: 999_automation_scrape_logs
Revises: (latest migration)
Create Date: 2026-09-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '999_automation_scrape_logs'
down_revision = None  # Separate branch - will be handled separately
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'automation_scrape_logs',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('competition_id', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('games_count', sa.Integer(), nullable=True),
        sa.Column('games_updated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), server_default=sa.func.now(), nullable=False, index=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('automation_scrape_logs')
