"""Add email and group fields to users."""
from alembic import op
import sqlalchemy as sa

revision = "20261028_000000"
down_revision = "20261027_000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=254), nullable=True))
    op.add_column("users", sa.Column("group_name", sa.String(length=120), nullable=True))
    op.create_index("ix_users_email_unique", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email_unique", table_name="users")
    op.drop_column("users", "group_name")
    op.drop_column("users", "email")