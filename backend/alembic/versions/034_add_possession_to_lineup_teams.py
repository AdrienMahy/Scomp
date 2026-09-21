"""Add possession column to lineup_teams table"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '034_add_possession_to_lineup_teams'
down_revision = '033_add_lineup_player_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add possession column to lineup_teams
    op.add_column('lineup_teams', sa.Column('possession', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove possession column from lineup_teams
    op.drop_column('lineup_teams', 'possession')
