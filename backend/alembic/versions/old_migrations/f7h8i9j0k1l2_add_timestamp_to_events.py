"""add_timestamp_to_events

Revision ID: f7h8i9j0k1l2
Revises: e6f7g8h9i0j1
Create Date: 2026-08-18 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7h8i9j0k1l2'
down_revision = 'e6f7g8h9i0j1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add timestamp column to game_goals
    op.add_column('game_goals', sa.Column('timestamp', sa.Float(), nullable=True))
    
    # Add timestamp column to game_cards
    op.add_column('game_cards', sa.Column('timestamp', sa.Float(), nullable=True))
    
    # Add timestamp column to game_substitutions
    op.add_column('game_substitutions', sa.Column('timestamp', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove timestamp column from game_substitutions
    op.drop_column('game_substitutions', 'timestamp')
    
    # Remove timestamp column from game_cards
    op.drop_column('game_cards', 'timestamp')
    
    # Remove timestamp column from game_goals
    op.drop_column('game_goals', 'timestamp')
