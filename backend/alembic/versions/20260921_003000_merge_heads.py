"""Merge the existing Alembic migration branches."""
from alembic import op


revision = "20260921_003000"
down_revision = (
    "060",
    "1a08f867f08e",
    "20260919_100000",
    "20260921_002000",
    "533627699ec0",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge heads without changing the existing database schema."""
    pass


def downgrade() -> None:
    """Return to the merged heads without changing the schema."""
    pass
