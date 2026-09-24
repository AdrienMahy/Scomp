"""PhysicalData database connection, isolated from TacticalData."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine


def get_physical_database_url() -> str:
    configured_url = os.getenv("PHYSICAL_DATABASE_URL")
    if configured_url:
        return configured_url

    project_root = Path(__file__).resolve().parents[4]
    values = dotenv_values(project_root / "config" / ".env")
    configured_url = values.get("PHYSICAL_DATABASE_URL")
    if not configured_url:
        raise RuntimeError("PHYSICAL_DATABASE_URL is not configured")
    return configured_url


@lru_cache(maxsize=1)
def get_physical_engine() -> Engine:
    return create_engine(get_physical_database_url(), pool_pre_ping=True)