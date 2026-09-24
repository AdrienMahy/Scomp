"""STATSports fetch and import workflows for the PhysicalData database."""

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from ..api.client import StatsportAPIClient
from ..api.config import StatsportSettings
from ..etl.export_dataset import build_dataset
from .persist_dataset import import_dataset, physical_database_url
from .scrape_logs import create_run, finish_run, write_log


def _api_date(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else value


def _activities(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    if isinstance(payload, dict):
        for key in ("activities", "sessions", "data", "result"):
            value = payload.get(key)
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
    raise ValueError("STATSports response does not contain an activity list")


def _third_party_api_id(settings: StatsportSettings) -> str:
    return (
        os.getenv("STATSPORT_API_ID")
        or os.getenv("STATSPORT_THIRD_PARTY_API_ID")
        or settings.api_token
    )


def _filter_squad(activities: list[dict[str, Any]], squad_external_id: str | None) -> list[dict[str, Any]]:
    if not squad_external_id:
        return activities
    return [activity for activity in activities
            if str((activity.get("sessionDetails") or {}).get("squadId")) == str(squad_external_id)]


async def process_activities(
    activities: list[dict[str, Any]],
    *,
    endpoint: str,
    request_payload: dict[str, Any],
    run_id: str | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    """Transform and import activities, with transaction isolation per activity."""
    database_url = database_url or physical_database_url(_project_env_path())
    if run_id:
        from sqlalchemy import create_engine
        engine = create_engine(database_url, pool_pre_ping=True)
        try:
            with engine.begin() as connection:
                write_log(connection, run_id, "INFO", "transform", "Transforming API activities into database records",
                          details={"activity_count": len(activities)})
        finally:
            engine.dispose()
    dataset = build_dataset(activities)
    for snapshot in dataset["tables"]["api_snapshots"]:
        snapshot["endpoint"] = endpoint
        snapshot["request_payload"] = request_payload
    result = import_dataset(dataset, database_url, run_id)
    result["found"] = len(activities)
    result["endpoint"] = endpoint
    if run_id:
        finish_run(database_url, run_id, result, status="partial" if result["failed"] else "completed")
        result["run_id"] = run_id
    return result


def _project_env_path():
    from pathlib import Path

    return Path(__file__).resolve().parents[4] / "config" / ".env"


async def _execute_scrape(
    *,
    scrape_type: str,
    display_name: str,
    endpoint: str,
    request_payload: dict[str, Any],
    fetch: Callable[[], Awaitable[Any]],
    database_url: str | None,
) -> dict[str, Any]:
    resolved_database_url = database_url or physical_database_url(_project_env_path())
    run_id = create_run(resolved_database_url, scrape_type, display_name, endpoint, request_payload)
    try:
        from sqlalchemy import create_engine
        engine = create_engine(resolved_database_url, pool_pre_ping=True)
        try:
            with engine.begin() as connection:
                write_log(connection, run_id, "INFO", "api_request", f"Calling {endpoint}", details=request_payload)
        finally:
            engine.dispose()
        payload = await fetch()
        engine = create_engine(resolved_database_url, pool_pre_ping=True)
        try:
            with engine.begin() as connection:
                write_log(connection, run_id, "INFO", "api_response", "STATSports response received")
        finally:
            engine.dispose()
        return await process_activities(_activities(payload), endpoint=endpoint,
                                        request_payload=request_payload, run_id=run_id,
                                        database_url=resolved_database_url)
    except Exception as error:
        error_message = str(error) or error.__class__.__name__
        finish_run(resolved_database_url, run_id, {}, status="failed", error_message=error_message)
        raise


async def scrape_by_share_date(
    share_date: date | str | None = None,
    *,
    settings: StatsportSettings | None = None,
    database_url: str | None = None,
    squad_external_id: str | None = None,
    scrape_type: str = "share_date",
    display_name: str = "Share date scrape",
) -> dict[str, Any]:
    settings = settings or StatsportSettings.from_env()
    share_date_value = share_date or datetime.now(timezone.utc).date().isoformat()
    request_payload = {"shareDate": _api_date(share_date_value)}
    if squad_external_id:
        request_payload["squadId"] = squad_external_id
    async def fetch():
        async with StatsportAPIClient(settings) as client:
            payload = await client.get_full_session_by_share_date(_third_party_api_id(settings), _api_date(share_date_value))
        return _filter_squad(_activities(payload), squad_external_id)
    return await _execute_scrape(scrape_type=scrape_type, display_name=display_name,
                                 endpoint="getFullSessionByShareDate", request_payload=request_payload,
                                 fetch=fetch, database_url=database_url)


async def scrape_by_date_range(
    start_date: date | str,
    end_date: date | str,
    *,
    settings: StatsportSettings | None = None,
    database_url: str | None = None,
    squad_external_id: str | None = None,
) -> dict[str, Any]:
    settings = settings or StatsportSettings.from_env()
    start_value, end_value = _api_date(start_date), _api_date(end_date)
    request_payload = {"sessionStartDate": start_value, "sessionEndDate": end_value}
    if squad_external_id:
        request_payload["squadId"] = squad_external_id
    async def fetch():
        async with StatsportAPIClient(settings) as client:
            current = date.fromisoformat(start_value)
            last = date.fromisoformat(end_value)
            activities: list[dict[str, Any]] = []
            while current <= last:
                day = current.isoformat()
                payload = await client.get_full_sessions_by_date_range(_third_party_api_id(settings), day, day)
                activities.extend(_activities(payload))
                current += timedelta(days=1)
        activities = [activity for activity in activities
                  if start_value <= str((activity.get("sessionDetails") or {}).get("sessionDate", ""))[:10] <= end_value]
        return _filter_squad(activities, squad_external_id)
    return await _execute_scrape(scrape_type="date_range", display_name="Date range scrape",
                                 endpoint="getFullSessionsByDateRange", request_payload=request_payload,
                                 fetch=fetch, database_url=database_url)


async def scrape_activity(
    session_date: date | str,
    activity_id: str,
    *,
    settings: StatsportSettings | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    settings = settings or StatsportSettings.from_env()
    session_date_value = _api_date(session_date)
    request_payload = {"sessionDate": session_date_value, "activityId": activity_id}
    async def fetch():
        async with StatsportAPIClient(settings) as client:
            payload = await client.get_full_session(_third_party_api_id(settings), session_date_value)
        activities = [activity for activity in _activities(payload) if str(activity.get("id")) == str(activity_id)]
        if not activities:
            raise ValueError(f"Activity {activity_id} was not found for session date {session_date_value}")
        return activities
    return await _execute_scrape(scrape_type="activity_id", display_name="Activity ID scrape",
                                 endpoint="getFullSession", request_payload=request_payload,
                                 fetch=fetch, database_url=database_url)