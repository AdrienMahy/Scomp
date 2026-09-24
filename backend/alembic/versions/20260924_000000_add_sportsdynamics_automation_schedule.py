"""Add schedule windows to SportsDynamics automation configurations"""
from alembic import op
import sqlalchemy as sa


revision = "20260924_000000"
down_revision = "20260921_002000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "automation_configurations",
        sa.Column("window_start_utc", sa.String(8), server_default="00:00:00", nullable=False),
    )
    op.add_column(
        "automation_configurations",
        sa.Column("window_end_utc", sa.String(8), server_default="23:59:59", nullable=False),
    )
    op.add_column(
        "automation_configurations",
        sa.Column("weekdays", sa.String(20), server_default="0,1,2,3,4,5,6", nullable=False),
    )


def downgrade():
    op.drop_column("automation_configurations", "weekdays")
    op.drop_column("automation_configurations", "window_end_utc")
    op.drop_column("automation_configurations", "window_start_utc")