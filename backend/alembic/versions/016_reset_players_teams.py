"""Add FK constraint from players to teams

Revision ID: 016_add_players_teams_fk
Revises: 015_event_tables
Create Date: 2026-09-01 10:00:00.000000

This migration:
1. Adds FK constraint from players.current_team_id to teams.id
2. Sets existing invalid team_ids to NULL
3. Ensures data integrity going forward

Note: Data cleanup is handled by the migration itself.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016_add_players_teams_fk'
down_revision = '015_event_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add FK constraint from players to teams"""
    
    # ========================================================================
    # STEP 1: Clean up invalid team_ids (those not in teams table)
    # ========================================================================
    op.execute("""
        UPDATE players p
        SET current_team_id = NULL, current_team_brand = NULL
        WHERE current_team_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM teams t WHERE t.id = p.current_team_id
          )
    """)
    
    # ========================================================================
    # STEP 2: Add FK constraint to ensure future data integrity
    # ========================================================================
    op.create_foreign_key(
        'fk_players_current_team_id',
        'players', 'teams',
        ['current_team_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade():
    """Rollback FK constraint"""
    op.drop_constraint('fk_players_current_team_id', 'players', type_='foreignkey')
