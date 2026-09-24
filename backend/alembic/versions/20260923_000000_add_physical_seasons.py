"""Add configurable PhysicalData seasons and link imported sessions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260923_000000"
down_revision = "20260922_003000"
branch_labels = None
depends_on = None
SCHEMA = "physical"


def upgrade() -> None:
    op.execute("SET LOCAL search_path TO physical, public")
    op.create_table(
        "seasons",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("start_date < end_date", name="ck_physical_seasons_date_order"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("start_date", name="uq_physical_seasons_start_date"),
    )
    op.create_index("ix_physical_seasons_dates", "seasons", ["start_date", "end_date"])

    op.execute("""
        INSERT INTO seasons (id, name, start_date, end_date)
        VALUES
            ('f7d5b8b4-1c28-4f79-a5cc-202220230001', '2022-2023', '2022-06-15', '2023-06-15'),
            ('f7d5b8b4-1c28-4f79-a5cc-202320240001', '2023-2024', '2023-06-15', '2024-06-15'),
            ('f7d5b8b4-1c28-4f79-a5cc-202420250001', '2024-2025', '2024-06-15', '2025-06-15'),
            ('f7d5b8b4-1c28-4f79-a5cc-202520260001', '2025-2026', '2025-06-15', '2026-06-15'),
            ('f7d5b8b4-1c28-4f79-a5cc-202620270001', '2026-2027', '2026-06-15', '2027-06-15')
    """)

    op.add_column("sessions", sa.Column("season_id", postgresql.UUID(as_uuid=False), nullable=True))
    op.create_index("ix_sessions_season_id", "sessions", ["season_id"])
    op.create_foreign_key("sessions_season_id_fkey", "sessions", "seasons", ["season_id"], ["id"], ondelete="RESTRICT")
    op.execute("""
        UPDATE sessions AS session
        SET season_id = season_catalog.id
        FROM seasons AS season_catalog
        WHERE session.session_date::date >= season_catalog.start_date
          AND session.session_date::date < season_catalog.end_date
    """)


def downgrade() -> None:
    op.execute("SET LOCAL search_path TO physical, public")
    op.drop_constraint("sessions_season_id_fkey", "sessions", type_="foreignkey")
    op.drop_index("ix_sessions_season_id", table_name="sessions")
    op.drop_column("sessions", "season_id")
    op.drop_index("ix_physical_seasons_dates", table_name="seasons")
    op.drop_table("seasons")
