"""Add indices on home_team_id and away_team_id for query optimization

Revision ID: e4f5g6h7i8j9
Revises: d9e1f2a3b4c5
Create Date: 2026-08-15 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5g6h7i8j9'
down_revision: Union[str, None] = 'd9e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add indices for faster team queries
    op.create_index('ix_games_home_team_id', 'games', ['home_team_id'], unique=False)
    op.create_index('ix_games_away_team_id', 'games', ['away_team_id'], unique=False)


def downgrade() -> None:
    # Drop indices
    op.drop_index('ix_games_home_team_id', table_name='games')
    op.drop_index('ix_games_away_team_id', table_name='games')
