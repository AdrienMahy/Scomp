"""Create v_game_data_summary VIEW for game data row counts per table.

Revision ID: 029_create_game_data_summary_view
Revises: 028_create_crosses_view
Create Date: 2026-09-07 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '029_create_game_data_summary_view'
down_revision = '028_create_crosses_view'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create v_game_data_summary view with game data row counts
    # This simplified version includes the most important metrics
    op.execute("""
    CREATE OR REPLACE VIEW v_game_data_summary AS
    SELECT 
      g.id as game_id,
      g.name as game_name,
      (SELECT COUNT(*) FROM events WHERE game_id = g.id) as events_count,
      (SELECT COUNT(*) FROM goals WHERE game_id = g.id) as goals_count,
      (SELECT COUNT(*) FROM card WHERE game_id = g.id) as cards_count
    FROM games g;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_game_data_summary")
