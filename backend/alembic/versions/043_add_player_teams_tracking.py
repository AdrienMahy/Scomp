"""Add player teams tracking with current_team and history

Revision ID: 043_add_player_teams_tracking
Revises: 042_increase_distance_covered_varchar
Create Date: 2026-09-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '043_add_player_teams_tracking'
down_revision = '042_increase_distance_covered_varchar'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add teams JSON column to players table for tracking team history.
    
    Structure:
    {
        "current_team": {
            "id": "team-uuid",
            "brand": "team-name"
        },
        "history": [
            {
                "team_id": "metz-uuid",
                "team_name": "Metz",
                "team_brand": "Metz",
                "round_start": 1,
                "round_end": 5
            },
            ...
        ]
    }
    """
    op.add_column('players', sa.Column('teams', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('players', 'teams')
