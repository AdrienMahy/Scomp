"""Add foreign key constraint on players.current_team_id to teams.id

Revision ID: f5g6h7i8j9k0
Revises: e4f5g6h7i8j9
Create Date: 2026-08-15 12:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5g6h7i8j9k0'
down_revision: Union[str, None] = 'e4f5g6h7i8j9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, clean up orphaned team references by setting them to NULL
    op.execute("""
        UPDATE players
        SET current_team_id = NULL
        WHERE current_team_id IS NOT NULL 
          AND current_team_id NOT IN (SELECT id FROM teams)
    """)
    
    # Add foreign key constraint on current_team_id
    op.create_foreign_key(
        'fk_players_current_team_id',
        'players',
        'teams',
        ['current_team_id'],
        ['id'],
        ondelete='SET NULL'
    )
    # Also add index for faster lookups
    op.create_index('ix_players_current_team_id', 'players', ['current_team_id'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_players_current_team_id', table_name='players')
    # Remove foreign key
    op.drop_constraint('fk_players_current_team_id', 'players', type_='foreignkey')
