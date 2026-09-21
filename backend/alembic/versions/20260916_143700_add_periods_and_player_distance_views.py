"""Add v_periods and v_player_distance_by_zone_interval views

Revision ID: 20260916_143700
Revises: 999_automation_scrape_logs
Create Date: 2026-09-16 14:37:00.000000

"""
from alembic import op
import sqlalchemy as sa
import os


# revision identifiers, used by Alembic.
revision = '20260916_143700'
down_revision = '7360e1209399'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply views upgrade"""
    # Read and execute the views.sql file
    views_sql_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'views.sql'
    )
    
    if os.path.exists(views_sql_path):
        with open(views_sql_path, 'r') as f:
            sql_statements = f.read()
        
        # Execute the SQL file
        op.execute(sa.text(sql_statements))
    else:
        raise FileNotFoundError(f"views.sql not found at {views_sql_path}")


def downgrade() -> None:
    """Downgrade by dropping the views"""
    op.execute("DROP VIEW IF EXISTS v_player_distance_by_zone_interval CASCADE;")
    op.execute("DROP VIEW IF EXISTS v_periods CASCADE;")
