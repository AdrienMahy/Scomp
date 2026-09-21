"""Enhance scraping task tracking with workflows and phases."""
from alembic import op
import sqlalchemy as sa


revision = "20260919_100000"
down_revision = "20260917_142000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'partial'")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'skipped'")

    op.add_column(
        "scraping_tasks",
        sa.Column("workflow", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "scraping_tasks",
        sa.Column("round_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "scraping_tasks",
        sa.Column("current_phase", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "scraping_tasks",
        sa.Column("current_item_id", sa.String(length=50), nullable=True),
    )
    op.execute("UPDATE scraping_tasks SET workflow = 'unknown' WHERE workflow IS NULL")
    op.alter_column("scraping_tasks", "workflow", nullable=False)
    op.create_index("ix_scraping_tasks_workflow", "scraping_tasks", ["workflow"])
    op.create_index("ix_scraping_tasks_round_name", "scraping_tasks", ["round_name"])


def downgrade() -> None:
    op.drop_index("ix_scraping_tasks_round_name", table_name="scraping_tasks")
    op.drop_index("ix_scraping_tasks_workflow", table_name="scraping_tasks")
    op.drop_column("scraping_tasks", "current_item_id")
    op.drop_column("scraping_tasks", "current_phase")
    op.drop_column("scraping_tasks", "round_name")
    op.drop_column("scraping_tasks", "workflow")
