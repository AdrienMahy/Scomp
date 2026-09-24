"""Persistence helpers for detailed PhysicalData scrape executions."""

import json
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, text


def json_value(value: Any) -> str | None:
    return None if value is None else json.dumps(value, ensure_ascii=True)


def create_run(database_url: str, scrape_type: str, display_name: str, endpoint: str, request_payload: dict[str, Any]) -> str:
    run_id = str(uuid4())
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO scrape_runs (id, scrape_type, display_name, endpoint, request_payload)
                VALUES (CAST(:id AS uuid), :scrape_type, :display_name, :endpoint, CAST(:request_payload AS jsonb))
            """), {"id": run_id, "scrape_type": scrape_type, "display_name": display_name,
                    "endpoint": endpoint, "request_payload": json_value(request_payload)})
            write_log(connection, run_id, "INFO", "run_started", f"Started {display_name}", details=request_payload)
    finally:
        engine.dispose()
    return run_id


def write_log(connection: Any, run_id: str, level: str, step: str, message: str,
              *, activity_id: str | None = None, activity_name: str | None = None,
              details: dict[str, Any] | None = None) -> None:
    connection.execute(text("""
        INSERT INTO scrape_logs (id, run_id, sequence_no, level, step, message, activity_id, activity_name, details)
        VALUES (CAST(:id AS uuid), CAST(:run_id AS uuid),
                COALESCE((SELECT MAX(sequence_no) + 1 FROM scrape_logs WHERE run_id = CAST(:run_id AS uuid)), 1),
                :level, :step, :message, CAST(:activity_id AS uuid), :activity_name, CAST(:details AS jsonb))
    """), {"id": str(uuid4()), "run_id": run_id, "level": level, "step": step,
            "message": message, "activity_id": activity_id, "activity_name": activity_name,
            "details": json_value(details)})


def finish_run(database_url: str, run_id: str, result: dict[str, Any], *, status: str = "completed",
               error_message: str | None = None) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                UPDATE scrape_runs SET status = :status, found = :found, inserted = :inserted,
                    updated = :updated, skipped = :skipped, failed = :failed,
                    error_message = :error_message, completed_at = now()
                WHERE id = CAST(:run_id AS uuid)
            """), {"run_id": run_id, "status": status, "found": result.get("found", 0),
                    "inserted": result.get("inserted", 0), "updated": result.get("updated", 0),
                    "skipped": result.get("skipped", 0), "failed": result.get("failed", 0),
                    "error_message": error_message})
            write_log(connection, run_id, "ERROR" if status == "failed" else "INFO", "run_finished",
                      f"Scrape {status}", details=result)
    finally:
        engine.dispose()