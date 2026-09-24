"""PhysicalData database connection, isolated from TacticalData."""

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine


def get_physical_database_url() -> str:
    configured_url = os.getenv("PHYSICAL_DATABASE_URL")
    if configured_url:
        return configured_url

    project_root = Path(__file__).resolve().parents[4]
    values = dotenv_values(project_root / "config" / ".env")
    database_url = values.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("PHYSICAL_DATABASE_URL is not configured")

    parsed = urlparse(database_url)
    return urlunparse(parsed._replace(path="/PhysicalData"))


@lru_cache(maxsize=1)
def get_physical_engine() -> Engine:
    return create_engine(get_physical_database_url(), pool_pre_ping=True)