"""Add CASCADE delete to all game_id foreign keys

Revision ID: 533627699ec0
Revises: 031_add_stats_to_scraping_logs
Create Date: 2026-09-07 17:08:41.165326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '533627699ec0'
down_revision: Union[str, None] = '031_add_stats_to_scraping_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
