"""Increase error_message column length in scraping_tasks

Revision ID: 038_increase_error_message_length
Revises: 037_fix_fitness_entities_fk_types
Create Date: 2026-09-09 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '038_increase_error_message_length'
down_revision = '037_fix_fitness_entities_fk_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Increase error_message column from VARCHAR(1000) to VARCHAR(5000)
    op.alter_column(
        'scraping_tasks',
        'error_message',
        existing_type=sa.String(1000),
        type_=sa.String(5000),
        existing_nullable=True
    )


def downgrade() -> None:
    # Revert to VARCHAR(1000)
    op.alter_column(
        'scraping_tasks',
        'error_message',
        existing_type=sa.String(5000),
        type_=sa.String(1000),
        existing_nullable=True
    )
