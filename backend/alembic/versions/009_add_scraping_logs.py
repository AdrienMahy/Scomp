"""Add scraping logs table

Revision ID: 009_add_scraping_logs
Revises: 008_add_data_processed_flag
Create Date: 2026-08-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '009_add_scraping_logs'
down_revision = '008_add_data_processed_flag'
branch_labels = None
depends_on = None


def upgrade():
    # Create scraping_logs table
    op.create_table(
        'scraping_logs',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('task_id', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('context', sa.String(length=100), nullable=True),
        sa.Column('item_id', sa.String(length=50), nullable=True),
        sa.Column('item_name', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_scraping_logs_task_id', 'scraping_logs', ['task_id'], unique=False)
    op.create_index('ix_scraping_logs_timestamp', 'scraping_logs', ['timestamp'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_scraping_logs_timestamp', table_name='scraping_logs')
    op.drop_index('ix_scraping_logs_task_id', table_name='scraping_logs')
    
    # Drop table
    op.drop_table('scraping_logs')
