"""Add scraping tasks table

Revision ID: 010_add_scraping_tasks
Revises: 009_add_scraping_logs
Create Date: 2026-08-27 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_add_scraping_tasks'
down_revision = '009_add_scraping_logs'
branch_labels = None
depends_on = None


def upgrade():
    # Create scraping_tasks table
    op.create_table(
        'scraping_tasks',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('competition_id', sa.String(length=50), nullable=False),
        sa.Column('season_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='taskstatus'), nullable=False, server_default='pending'),
        sa.Column('total_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_scraping_tasks_competition_id', 'scraping_tasks', ['competition_id'], unique=False)
    op.create_index('ix_scraping_tasks_season_id', 'scraping_tasks', ['season_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_scraping_tasks_season_id', table_name='scraping_tasks')
    op.drop_index('ix_scraping_tasks_competition_id', table_name='scraping_tasks')
    
    # Drop table
    op.drop_table('scraping_tasks')
