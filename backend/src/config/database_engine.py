"""Helpers for creating database engines with per-service pool settings."""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url


def create_configured_engine(
    database_url: str,
    *,
    env_prefix: str,
    default_pool_size: int,
    default_max_overflow: int,
    echo: bool = False,
) -> Engine:
    options: dict[str, object] = {"echo": echo, "pool_pre_ping": True}

    if make_url(database_url).get_backend_name() == "postgresql":
        options["pool_size"] = int(
            os.getenv(f"{env_prefix}_POOL_SIZE", default_pool_size)
        )
        options["max_overflow"] = int(
            os.getenv(f"{env_prefix}_MAX_OVERFLOW", default_max_overflow)
        )

        connect_args: dict[str, str] = {}
        application_name = os.getenv(f"{env_prefix}_APPLICATION_NAME")
        idle_timeout_ms = os.getenv(f"{env_prefix}_IDLE_SESSION_TIMEOUT_MS")
        if application_name:
            connect_args["application_name"] = application_name
        if idle_timeout_ms is not None:
            connect_args["options"] = f"-c idle_session_timeout={int(idle_timeout_ms)}"
        if connect_args:
            options["connect_args"] = connect_args

    return create_engine(database_url, **options)
