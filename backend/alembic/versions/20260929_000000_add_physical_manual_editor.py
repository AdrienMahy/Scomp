"""Store manual PhysicalData editor values without altering imported drills."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260929_000000"
down_revision = "20260923_001000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manual_drill_values",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("drill_metadata_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("metric_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["drill_metadata_id"], ["drill_metadata.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "player_id", "drill_metadata_id"),
    )
    for column in ("session_id", "player_id", "drill_metadata_id"):
        op.create_index(f"ix_manual_drill_values_{column}", "manual_drill_values", [column])


def downgrade() -> None:
    op.drop_table("manual_drill_values")
