"""Add OutputFile table for tracking game output files

Revision ID: 006_add_output_files_table
Revises: 005_add_missing_game_columns
Create Date: 2026-08-26 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_output_files_table'
down_revision = '005_add_missing_game_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Create output_files table
    op.create_table(
        'output_files',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('is_outdated', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('file_size', sa.String(50), nullable=True),
        sa.Column('file_name_raw', sa.String(255), nullable=True),
        sa.Column('available', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('downloaded_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], name='output_files_game_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_output_files_game_id', 'game_id'),
    )


def downgrade():
    op.drop_table('output_files')
