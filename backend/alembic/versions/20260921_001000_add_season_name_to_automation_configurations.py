"""Add season name to automation configurations"""
from alembic import op
import sqlalchemy as sa


revision = "20260921_001000"
down_revision = "20260921_000000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "automation_configurations",
        sa.Column("season_name", sa.String(255), nullable=True),
    )


def downgrade():
    op.drop_column("automation_configurations", "season_name")