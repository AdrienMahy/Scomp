"""Track PhysicalData session presence in the upstream API."""

from alembic import op
import sqlalchemy as sa

revision = "20260929_010000"
down_revision = "20260929_000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("source_status", sa.String(length=16), nullable=False, server_default="active"))
    op.add_column("sessions", sa.Column("missing_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("sessions", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sessions", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_sessions_source_status", "sessions", ["source_status"])


def downgrade() -> None:
    op.drop_index("ix_sessions_source_status", table_name="sessions")
    op.drop_column("sessions", "deleted_at")
    op.drop_column("sessions", "last_seen_at")
    op.drop_column("sessions", "missing_count")
    op.drop_column("sessions", "source_status")
