"""Add game_status table

Revision ID: 004_add_game_status
Revises: 003_add_competitions_and_seasons
Create Date: 2026-08-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '004_add_game_status'
down_revision = '003_add_competitions_and_seasons'
branch_labels = None
depends_on = None


def upgrade():
    """Create game_status table"""
    
    op.create_table(
        'game_status',
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('available', sa.Boolean(), default=False),
        sa.Column('is_ugd_available', sa.Boolean(), default=False),
        sa.Column('rgd_status', sa.String(50)),
        sa.Column('ugd_status', sa.String(50)),
        sa.Column('output_files', postgresql.JSONB(astext_type=sa.Text()), default=sa.literal([])),
        sa.Column('output_files_hash', sa.String(64)),
        sa.Column('last_checked_at', sa.DateTime()),
        sa.Column('status_changed_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('game_id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_game_status_game_id', 'game_status', ['game_id'])
    op.create_index('idx_game_status_available', 'game_status', ['available'])
    op.create_index('idx_game_status_rgd', 'game_status', ['rgd_status'])


def downgrade():
    """Drop game_status table"""
    
    op.drop_index('idx_game_status_rgd', 'game_status')
    op.drop_index('idx_game_status_available', 'game_status')
    op.drop_index('idx_game_status_game_id', 'game_status')
    op.drop_table('game_status')
