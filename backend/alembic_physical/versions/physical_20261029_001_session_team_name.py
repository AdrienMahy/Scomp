"""Persist team names parsed from PhysicalData session names."""

from alembic import op


revision = "physical_20261029_001"
down_revision = "physical_20261029_000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS team_name TEXT")
    op.execute("""
        UPDATE public.sessions
        SET team_name = NULLIF(BTRIM(split_part(activity_name, ' - ', 1)), '')
        WHERE activity_name IS NOT NULL
          AND position(' - ' IN activity_name) > 0
          AND BTRIM(substring(activity_name FROM position(' - ' IN activity_name) + 3)) <> ''
          AND team_name IS DISTINCT FROM NULLIF(BTRIM(split_part(activity_name, ' - ', 1)), '')
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_sessions_team_name_lower ON public.sessions (lower(team_name))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_sessions_team_name_lower")
    op.execute("ALTER TABLE public.sessions DROP COLUMN IF EXISTS team_name")