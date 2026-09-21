"""make_period_and_frame_nullable_in_game_goals_and_cards

Revision ID: 7360e1209399
Revises: 6dcc34fca6d1
Create Date: 2026-09-08 10:23:42.218506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7360e1209399'
down_revision: Union[str, None] = '6dcc34fca6d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
