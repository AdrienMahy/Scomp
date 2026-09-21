"""make_card_type_nullable

Revision ID: 1a08f867f08e
Revises: 7360e1209399
Create Date: 2026-09-08 10:25:32.244154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a08f867f08e'
down_revision: Union[str, None] = '7360e1209399'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
