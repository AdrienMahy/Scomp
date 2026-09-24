"""Preserve event order in PhysicalData scrape logs."""

from alembic import op
import sqlalchemy as sa


revision = "20260922_003000"
down_revision = "20260922_002000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL search_path TO physical, public")
    op.add_column("scrape_logs", sa.Column("sequence_no", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE scrape_logs AS current_log
        SET sequence_no = ordered.sequence_no
        FROM (
            SELECT id, row_number() OVER (PARTITION BY run_id ORDER BY timestamp, id) AS sequence_no
            FROM scrape_logs
        ) AS ordered
        WHERE current_log.id = ordered.id
    """)
    op.alter_column("scrape_logs", "sequence_no", nullable=False)
    op.create_unique_constraint("uq_scrape_logs_run_sequence", "scrape_logs", ["run_id", "sequence_no"])


def downgrade() -> None:
    op.execute("SET LOCAL search_path TO physical, public")
    op.drop_constraint("uq_scrape_logs_run_sequence", "scrape_logs", type_="unique")
    op.drop_column("scrape_logs", "sequence_no")