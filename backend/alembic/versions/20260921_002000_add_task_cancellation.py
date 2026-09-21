"""Add cooperative cancellation to scraping tasks."""
from alembic import op
import sqlalchemy as sa


revision = "20260921_002000"
down_revision = "20260921_001000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'cancelled'")
    op.add_column(
        "scraping_tasks",
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("scraping_tasks", "cancel_requested")
    # PostgreSQL does not support removing an enum value directly.
