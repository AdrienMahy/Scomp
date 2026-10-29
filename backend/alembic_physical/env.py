import os
from pathlib import Path

from alembic import context
from dotenv import dotenv_values
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


config = context.config
project_root = Path(__file__).resolve().parents[2]
values = {**dotenv_values(project_root / "config" / ".env"), **os.environ}
database_url = values.get("PHYSICAL_DATABASE_URL")
if not database_url:
    raise ValueError("PHYSICAL_DATABASE_URL is not configured")

VERSION_TABLE = "physical_alembic_version"


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url, poolclass=NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table=VERSION_TABLE,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()