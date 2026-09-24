"""Add weekday-aware PhysicalData automation rules."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260923_001000"
down_revision = "20260923_000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "automation_configurations",
        sa.Column(
            "weekdays",
            postgresql.ARRAY(sa.SmallInteger()),
            nullable=False,
            server_default=sa.text("'{0,1,2,3,4,5,6}'::smallint[]"),
        ),
    )


def downgrade() -> None:
    op.drop_column("automation_configurations", "weekdays")
