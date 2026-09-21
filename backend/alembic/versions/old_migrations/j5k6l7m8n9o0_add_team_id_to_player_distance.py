"""Add team_id to player_distance_covered model

Revision ID: j5k6l7m8n9o0
Revises: i0k1l2m3n4o5
Create Date: 2026-08-18 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'j5k6l7m8n9o0'
down_revision = 'i0k1l2m3n4o5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add team_id column to player_distance_covered
    op.add_column('player_distance_covered', sa.Column('team_id', sa.String(36), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_player_distance_covered_team_id',
        'player_distance_covered',
        'teams',
        ['team_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Add index for better query performance
    op.create_index(
        'ix_player_distance_covered_team_id',
        'player_distance_covered',
        ['team_id']
    )


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_player_distance_covered_team_id', table_name='player_distance_covered')
    
    # Remove foreign key
    op.drop_constraint('fk_player_distance_covered_team_id', 'player_distance_covered', type_='foreignkey')
    
    # Remove column
    op.drop_column('player_distance_covered', 'team_id')
