"""Remove the obsolete automation scrape log table."""
from alembic import op


revision = "20260919_110000"
down_revision = "999_automation_scrape_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS automation_scrape_logs")


def downgrade() -> None:
    raise RuntimeError("automation_scrape_logs was intentionally removed; restore from a backup to downgrade")