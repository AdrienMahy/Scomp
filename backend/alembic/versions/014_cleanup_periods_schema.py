"""Remove period_number column and clean up periods schema

Revision ID: 014_cleanup_periods_schema
Revises: 013_fix_periods_id_type
Create Date: 2026-08-27 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014_cleanup_periods_schema'
down_revision = '013_fix_periods_id_type'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the old period_number column since we're using period_id now
    op.drop_column('periods', 'period_number')


def downgrade():
    # Recreate the period_number column if downgrading
    op.add_column('periods', sa.Column('period_number', sa.Integer(), nullable=False, server_default='0'))
