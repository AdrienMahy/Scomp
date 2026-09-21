"""make_player_id_nullable_in_game_goals_and_cards

Revision ID: e6124c7556ae
Revises: 030_add_round_to_scraping_logs
Create Date: 2026-09-08 10:13:24.222640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6124c7556ae'
down_revision: Union[str, None] = '029_create_game_data_summary_view'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
