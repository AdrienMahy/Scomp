"""make_team_id_nullable_in_specialized_event_tables

Revision ID: 6dcc34fca6d1
Revises: e6124c7556ae
Create Date: 2026-09-08 10:22:16.315237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6dcc34fca6d1'
down_revision: Union[str, None] = 'e6124c7556ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
