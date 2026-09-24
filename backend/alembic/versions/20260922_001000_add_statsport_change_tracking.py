"""Add STATSport activity versions, latest snapshots, and automation settings."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260922_001000"
down_revision = "20260922_000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL search_path TO physical, public")
    op.add_column("sessions", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    op.add_column("api_snapshots", sa.Column("activity_id", postgresql.UUID(as_uuid=False), nullable=True))
    op.execute("DELETE FROM api_snapshots WHERE activity_id IS NULL")
    op.create_foreign_key(
        "fk_api_snapshots_activity_id",
        "api_snapshots",
        "sessions",
        ["activity_id"],
        ["activity_id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint("uq_api_snapshots_activity_id", "api_snapshots", ["activity_id"])

    op.create_table(
        "automation_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("window_start_utc", sa.Time(), nullable=False, server_default="00:00:00"),
        sa.Column("window_end_utc", sa.Time(), nullable=False, server_default="23:59:59"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.CheckConstraint("interval_minutes > 0", name="ck_physical_automation_interval_positive"),
        sa.CheckConstraint("window_start_utc <= window_end_utc", name="ck_physical_automation_window_order"),
    )


def downgrade() -> None:
    op.execute("SET LOCAL search_path TO physical, public")
    op.drop_table("automation_configurations")
    op.drop_constraint("uq_api_snapshots_activity_id", "api_snapshots", type_="unique")
    op.drop_constraint("fk_api_snapshots_activity_id", "api_snapshots", type_="foreignkey")
    op.drop_column("api_snapshots", "activity_id")
    op.drop_column("sessions", "version")