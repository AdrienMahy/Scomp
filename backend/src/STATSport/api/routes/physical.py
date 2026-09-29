"""PhysicalData browsing and STATSports scraping control routes."""

from datetime import date, time
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.STATSport.models.database import get_physical_engine
from src.STATSport.api.client import StatsportAPIError
from src.STATSport.orchestration.orchestration import (
    scrape_activity,
    scrape_by_date_range,
    scrape_by_share_date,
)


router = APIRouter(prefix="/statsport/physical", tags=["statsport"])


def _activity_statuses(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    activities: dict[str, dict[str, Any]] = {}
    for log in logs:
        activity_id = log.get("activity_id")
        if not activity_id:
            continue
        key = str(activity_id)
        activity = activities.setdefault(key, {
            "activity_id": key,
            "activity_name": log.get("activity_name") or "Unnamed activity",
            "status": "processing",
            "reason": None,
        })
        details = log.get("details") or {}
        if log.get("step") in {"activity_failed", "quality_validation"}:
            activity["status"] = "failed"
            activity["reason"] = log.get("message") or "Activity processing failed"
        elif log.get("step") == "data_presence":
            activity["status"] = "skipped"
            activity["reason"] = log.get("message") or "Activity was already present and unchanged"
        elif log.get("step") == "persistence":
            activity["status"] = "updated" if details.get("updated") else "inserted"
            activity["reason"] = log.get("message")
    return list(activities.values())


class AutomationConfigurationUpdate(BaseModel):
    name: str = Field(default="statsport_daily", min_length=1, max_length=100)
    enabled: bool = False
    interval_minutes: int = Field(default=1440, ge=1)
    window_start_utc: time = time(0, 0)
    window_end_utc: time = time(23, 59, 59)
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1)


class SquadNameUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SeasonUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date


EDITOR_METRICS = {
    "distanceTotal": "distance",
    "distancePerMin": "distance",
    "sprintDistance": "distance",
    "accelerationsAbs": "acceleration",
    "accelerationsRel": "acceleration",
    "maxAcceleration": "acceleration",
    "totalAccelLoading": "acceleration",
}
EXCLUDED_EDITOR_DRILLS = {"entire session", "entire session - live"}


class ManualMetricsUpdate(BaseModel):
    session_id: str
    player_id: str
    drill_metadata_id: str
    metrics: dict[str, float | None]


class ManualEditorRow(BaseModel):
    drill_metadata_id: str
    metrics: dict[str, float | None]


class ManualEditorSave(BaseModel):
    session_id: str
    player_id: str
    rows: list[ManualEditorRow] = Field(min_length=1)


class ManualBulkUpdate(BaseModel):
    session_id: str
    player_id: str
    drill_metadata_ids: list[str] = Field(min_length=1)
    action: str
    source_player_id: str | None = None
    persist: bool = False


def _scrape_error(error: Exception) -> HTTPException:
    status_code = error.status_code if isinstance(error, StatsportAPIError) and error.status_code else 502
    return HTTPException(status_code=status_code, detail=str(error))


@router.post("/scraping/automation/run")
async def run_automation(share_date: date | None = Query(default=None), squad_external_id: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        return await scrape_by_share_date(share_date, squad_external_id=squad_external_id)
    except (StatsportAPIError, ValueError) as error:
        raise _scrape_error(error) from error


@router.post("/scraping/range-date")
async def run_date_range(start_date: date, end_date: date, squad_external_id: str | None = Query(default=None)) -> dict[str, Any]:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    try:
        return await scrape_by_date_range(start_date, end_date, squad_external_id=squad_external_id)
    except (StatsportAPIError, ValueError) as error:
        raise _scrape_error(error) from error


@router.post("/scraping/activity")
async def run_activity(session_date: date, activity_id: str) -> dict[str, Any]:
    try:
        return await scrape_activity(session_date, activity_id)
    except (StatsportAPIError, ValueError) as error:
        raise _scrape_error(error) from error


def _validate_automation_rule(configuration: AutomationConfigurationUpdate) -> None:
    if any(day < 0 or day > 6 for day in configuration.weekdays):
        raise HTTPException(status_code=422, detail="weekdays must contain values from 0 (Monday) to 6 (Sunday)")
    if configuration.window_end_utc < configuration.window_start_utc:
        raise HTTPException(status_code=422, detail="window_end_utc must be on or after window_start_utc")


@router.get("/scraping/automation/config")
def get_automation_configuration() -> list[dict[str, Any]]:
    with get_physical_engine().connect() as connection:
        row = connection.execute(text("""
            SELECT id, name, enabled, interval_minutes, window_start_utc, window_end_utc, weekdays,
                   created_at, updated_at
            FROM automation_configurations ORDER BY name
        """)).mappings()
        return [dict(item) for item in row]


@router.put("/scraping/automation/config")
def update_automation_configuration(configuration: AutomationConfigurationUpdate) -> dict[str, Any]:
    _validate_automation_rule(configuration)
    values = configuration.model_dump()
    values["id"] = str(uuid4())
    with get_physical_engine().begin() as connection:
        row = connection.execute(text("""
            INSERT INTO automation_configurations (
                id, name, enabled, interval_minutes, window_start_utc, window_end_utc, weekdays
            ) VALUES (CAST(:id AS uuid), :name, :enabled, :interval_minutes,
                      :window_start_utc, :window_end_utc, :weekdays)
            ON CONFLICT (name) DO UPDATE SET enabled = EXCLUDED.enabled,
                interval_minutes = EXCLUDED.interval_minutes,
                window_start_utc = EXCLUDED.window_start_utc,
                window_end_utc = EXCLUDED.window_end_utc,
                weekdays = EXCLUDED.weekdays,
                updated_at = now()
            RETURNING id, name, enabled, interval_minutes, window_start_utc, window_end_utc, weekdays,
                      created_at, updated_at
        """), {**values, "name": configuration.name}).mappings().one()
    return dict(row)


@router.delete("/scraping/automation/config/{name}", status_code=204)
def delete_automation_configuration(name: str) -> None:
    with get_physical_engine().begin() as connection:
        result = connection.execute(text("DELETE FROM automation_configurations WHERE name = :name"), {"name": name})
    if not result.rowcount:
        raise HTTPException(status_code=404, detail="Automation rule not found")


@router.get("/scraping/automation/overview")
def automation_overview(limit: int = Query(default=12, ge=1, le=100)) -> dict[str, Any]:
    with get_physical_engine().connect() as connection:
        rules = connection.execute(text("""
            SELECT id, name, enabled, interval_minutes, window_start_utc, window_end_utc, weekdays
            FROM automation_configurations ORDER BY name
        """)).mappings()
        runs = connection.execute(text("""
            SELECT id, scrape_type, display_name, status, found, inserted, updated, skipped, failed,
                   error_message, started_at, completed_at
            FROM scrape_runs
            WHERE scrape_type IN ('statsport_daily', 'statsport_automation')
            ORDER BY started_at DESC LIMIT :limit
        """), {"limit": limit}).mappings()
    return {"rules": [dict(rule) for rule in rules], "runs": [dict(run) for run in runs]}


@router.get("/squads")
def list_squads() -> list[dict[str, Any]]:
    with get_physical_engine().connect() as connection:
        rows = connection.execute(text("""
            SELECT id, external_id, name
            FROM squads
            ORDER BY name NULLS LAST, external_id
        """)).mappings()
        return [dict(row) for row in rows]


@router.put("/squads/{squad_id}")
def update_squad_name(squad_id: str, update: SquadNameUpdate) -> dict[str, Any]:
    if not update.name.strip():
        raise HTTPException(status_code=422, detail="Squad name cannot be empty")
    with get_physical_engine().begin() as connection:
        row = connection.execute(text("""
            UPDATE squads SET name = :name
            WHERE id = CAST(:squad_id AS uuid)
            RETURNING id, external_id, name
        """), {"squad_id": squad_id, "name": update.name.strip()}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Squad not found")
    return dict(row)


@router.get("/seasons")
def list_seasons() -> list[dict[str, Any]]:
    with get_physical_engine().connect() as connection:
        rows = connection.execute(text("""
            SELECT id, name, start_date, end_date, created_at, updated_at,
                             (SELECT count(*) FROM sessions WHERE sessions.season_id = seasons.id) AS activity_count
                         FROM seasons
            ORDER BY start_date DESC
        """)).mappings()
        return [dict(row) for row in rows]


def _validate_season(connection: Any, season: SeasonUpdate, season_id: str | None = None) -> None:
    if season.end_date <= season.start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    overlap = connection.execute(text("""
        SELECT 1
        FROM seasons
        WHERE start_date < :end_date AND end_date > :start_date
          AND (:season_id IS NULL OR id <> CAST(:season_id AS uuid))
        LIMIT 1
    """), {"start_date": season.start_date, "end_date": season.end_date, "season_id": season_id}).first()
    if overlap:
        raise HTTPException(status_code=409, detail="Season dates overlap an existing season")


@router.post("/seasons")
def create_season(season: SeasonUpdate) -> dict[str, Any]:
    season_id = str(uuid4())
    with get_physical_engine().begin() as connection:
        _validate_season(connection, season)
        row = connection.execute(text("""
            INSERT INTO seasons (id, name, start_date, end_date)
            VALUES (CAST(:id AS uuid), :name, :start_date, :end_date)
            RETURNING id, name, start_date, end_date, created_at, updated_at
        """), {"id": season_id, **season.model_dump()}).mappings().one()
    return dict(row)


@router.put("/seasons/{season_id}")
def update_season(season_id: str, season: SeasonUpdate) -> dict[str, Any]:
    with get_physical_engine().begin() as connection:
        _validate_season(connection, season, season_id)
        row = connection.execute(text("""
            UPDATE seasons
            SET name = :name, start_date = :start_date, end_date = :end_date, updated_at = now()
            WHERE id = CAST(:id AS uuid)
            RETURNING id, name, start_date, end_date, created_at, updated_at
        """), {"id": season_id, **season.model_dump()}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Season not found")
    return dict(row)


@router.get("/sessions")
def list_sessions(
    squad_id: str | None = Query(default=None),
    activity_name: str | None = Query(default=None),
    session_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    filters = []
    params: dict[str, Any] = {"limit": limit}
    if squad_id:
        filters.append("s.squad_id = CAST(:squad_id AS uuid)")
        params["squad_id"] = squad_id
    if activity_name:
        filters.append("s.activity_name = :activity_name")
        params["activity_name"] = activity_name
    if session_date:
        filters.append("s.session_date::date = :session_date")
        params["session_date"] = session_date
    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    with get_physical_engine().connect() as connection:
        rows = connection.execute(text(f"""
                 SELECT s.id, s.activity_id, s.activity_name, s.share_date,
                   s.session_date, s.start_time, s.end_time, s.session_type,
                     s.squad_id, sq.external_id AS squad_external_id, sq.name AS squad_name,
                     s.season_id, se.name AS season_name
            FROM sessions s
            JOIN squads sq ON sq.id = s.squad_id
                 LEFT JOIN seasons se ON se.id = s.season_id
            {where_clause}{' AND ' if where_clause else 'WHERE '}s.source_status = 'active'
            ORDER BY s.session_date DESC, s.activity_name
            LIMIT :limit
        """), params).mappings()
        return [dict(row) for row in rows]


@router.get("/sessions/deleted")
def list_deleted_sessions(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
    with get_physical_engine().connect() as connection:
        rows = connection.execute(text("""
            SELECT s.id, s.activity_id, s.activity_name, s.share_date,
                   s.session_date, s.start_time, s.end_time, s.session_type,
                   s.squad_id, sq.external_id AS squad_external_id, sq.name AS squad_name,
                   s.deleted_at, s.missing_count, s.last_seen_at
            FROM sessions s
            JOIN squads sq ON sq.id = s.squad_id
            WHERE s.source_status = 'deleted'
            ORDER BY s.deleted_at DESC NULLS LAST, s.session_date DESC
            LIMIT :limit
        """), {"limit": limit}).mappings()
        return [dict(row) for row in rows]


@router.get("/players")
def list_players(
    search: str | None = Query(default=None, min_length=1),
    squad_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit}
    clauses = []
    if search:
        clauses.append("p.display_name ILIKE :search")
        params["search"] = f"%{search}%"
    if squad_id:
        clauses.append("EXISTS (SELECT 1 FROM session_players sp JOIN sessions s ON s.id = sp.session_id WHERE sp.player_id = p.id AND s.squad_id = CAST(:squad_id AS uuid))")
        params["squad_id"] = squad_id
    where_clause = "WHERE " + " AND ".join(clauses) if clauses else ""

    with get_physical_engine().connect() as connection:
        rows = connection.execute(text(f"""
            SELECT p.id, p.display_name, p.first_name, p.last_name,
                   p.primary_position, p.secondary_position, p.active_squad_name
            FROM players p
            {where_clause}
            ORDER BY p.display_name NULLS LAST
            LIMIT :limit
        """), params).mappings()
        return [dict(row) for row in rows]


@router.get("/players/all")
def list_all_players() -> list[dict[str, Any]]:
    with get_physical_engine().connect() as connection:
        rows = connection.execute(text("""
            SELECT p.id, p.display_name, p.first_name, p.last_name,
                   p.primary_position, p.secondary_position, p.active_squad_name
            FROM players p
            ORDER BY p.display_name NULLS LAST, p.last_name NULLS LAST, p.first_name NULLS LAST
        """)).mappings()
        return [dict(row) for row in rows]


@router.get("/logs")
def list_physical_logs(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
    with get_physical_engine().connect() as connection:
        rows = connection.execute(text("""
            SELECT id, scrape_type, display_name, endpoint, request_payload, status,
                   found, inserted, updated, skipped, failed, error_message,
                   started_at, completed_at
            FROM scrape_runs
            ORDER BY started_at DESC
            LIMIT :limit
        """), {"limit": limit}).mappings()
        return [dict(row) for row in rows]


@router.get("/logs/{run_id}")
def get_physical_log(run_id: str) -> dict[str, Any]:
    with get_physical_engine().connect() as connection:
        run = connection.execute(text("""
            SELECT id, scrape_type, display_name, endpoint, request_payload, status,
                   found, inserted, updated, skipped, failed, error_message,
                   started_at, completed_at
            FROM scrape_runs
            WHERE id = CAST(:run_id AS uuid)
        """), {"run_id": run_id}).mappings().first()
        if not run:
            raise HTTPException(status_code=404, detail="Scrape run not found")
        logs = connection.execute(text("""
            SELECT id, timestamp, sequence_no, level, step, message, activity_id, activity_name, details
            FROM scrape_logs
            WHERE run_id = CAST(:run_id AS uuid)
            ORDER BY sequence_no
        """), {"run_id": run_id}).mappings()
        log_entries = [dict(log) for log in logs]
        return {"run": dict(run), "logs": log_entries, "activities": _activity_statuses(log_entries)}


@router.get("/activities/{activity_id}/players/{player_id}")
def get_player_activity(activity_id: str, player_id: str) -> dict[str, Any]:
    with get_physical_engine().connect() as connection:
        player = connection.execute(text("""
            SELECT id, display_name, first_name, last_name,
                   primary_position, secondary_position, active_squad_name,
                   player_details
            FROM players
            WHERE id = CAST(:player_id AS uuid)
        """), {"player_id": player_id}).mappings().first()
        activity = connection.execute(text("""
            SELECT s.id, s.activity_id, s.activity_name, s.share_date,
                   s.session_date, s.start_time, s.end_time, s.session_type,
                   s.squad_id, s.raw_data
            FROM sessions s
            WHERE s.activity_id = CAST(:activity_id AS uuid)
        """), {"activity_id": activity_id}).mappings().first()

        if not player or not activity:
            raise HTTPException(status_code=404, detail="Player or activity not found")

        participation = connection.execute(text("""
            SELECT id, source_id, raw_data_id, player_details
            FROM session_players
            WHERE session_id = :session_id AND player_id = CAST(:player_id AS uuid)
        """), {"session_id": activity["id"], "player_id": player_id}).mappings().first()
        if not participation:
            raise HTTPException(status_code=404, detail="Player did not participate in this activity")

        drills = connection.execute(text("""
            SELECT d.id, d.source_id, d.session_player_data_id, d.start_time,
                   d.end_time, d.free_text, d.metrics, d.raw_data,
                   dm.drill_name, dm.primary_label, dm.secondary_label,
                   dm.tertiary_label, dm.session_type
            FROM drills d
            JOIN drill_metadata dm ON dm.id = d.drill_metadata_id
            WHERE d.session_player_id = :session_player_id
            ORDER BY d.start_time NULLS FIRST, dm.drill_name
        """), {"session_player_id": participation["id"]}).mappings()

        return {
            "player": dict(player),
            "activity": dict(activity),
            "participation": dict(participation),
            "drills": [dict(drill) for drill in drills],
        }


@router.get("/activities/{activity_id}")
def get_activity(activity_id: str) -> dict[str, Any]:
    with get_physical_engine().connect() as connection:
        activity = connection.execute(text("""
                 SELECT s.id, s.activity_id, s.activity_name, s.share_date,
                   s.session_date, s.start_time, s.end_time,
                   s.created_at AS processing_started_at,
                   s.updated_at AS processed_at,
                   s.session_type, s.squad_id, s.season_id, se.name AS season_name,
                   sq.external_id AS squad_external_id,
                   sq.name AS squad_name
            FROM sessions s
            JOIN squads sq ON sq.id = s.squad_id
            LEFT JOIN seasons se ON se.id = s.season_id
            WHERE s.activity_id = CAST(:activity_id AS uuid)
        """), {"activity_id": activity_id}).mappings().first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        players = connection.execute(text("""
            SELECT p.id, p.display_name, p.first_name, p.last_name,
                   p.primary_position, p.secondary_position,
                                     sp.player_details,
                                     CASE WHEN EXISTS (
                                             SELECT 1
                                             FROM manual_drill_values mdv
                                             WHERE mdv.session_id = sp.session_id
                                                 AND mdv.player_id = sp.player_id
                                     ) THEN '"Manual Data"'::json ELSE '[]'::json END AS active_squad_name
            FROM session_players sp
            JOIN players p ON p.id = sp.player_id
            WHERE sp.session_id = :session_id
            ORDER BY p.last_name NULLS LAST, p.first_name NULLS LAST, p.display_name
        """), {"session_id": activity["id"]}).mappings()
        drills = connection.execute(text("""
                 SELECT DISTINCT d.start_time, d.end_time,
                     dm.drill_name, dm.primary_label,
                   dm.secondary_label, dm.tertiary_label,
                   dm.session_type
            FROM drills d
            JOIN session_players sp ON sp.id = d.session_player_id
            JOIN drill_metadata dm ON dm.id = d.drill_metadata_id
            WHERE sp.session_id = :session_id
            ORDER BY d.start_time NULLS LAST, dm.drill_name, dm.primary_label
        """), {"session_id": activity["id"]}).mappings()

        return {
            "activity": dict(activity),
            "players": [dict(player) for player in players],
            "drills": [dict(drill) for drill in drills],
        }


def _editor_value(metrics: dict[str, Any] | None, metric: str) -> Any:
    category = EDITOR_METRICS[metric]
    return (metrics or {}).get(category, {}).get(metric)


def _editor_rows(connection: Any, session_id: str, player_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(text("""
        SELECT dm.id, dm.drill_name, dm.primary_label, dm.secondary_label,
               dm.tertiary_label, dm.session_type,
               d.metrics AS imported_metrics, mdv.metric_values AS manual_metrics
        FROM drill_metadata dm
        LEFT JOIN session_players sp
          ON sp.session_id = dm.session_id AND sp.player_id = CAST(:player_id AS uuid)
        LEFT JOIN LATERAL (
            SELECT d.metrics
            FROM drills d
            WHERE d.session_player_id = sp.id AND d.drill_metadata_id = dm.id
            ORDER BY d.start_time NULLS FIRST, d.id
            LIMIT 1
        ) d ON true
        LEFT JOIN manual_drill_values mdv
          ON mdv.session_id = dm.session_id
         AND mdv.player_id = CAST(:player_id AS uuid)
         AND mdv.drill_metadata_id = dm.id
        WHERE dm.session_id = CAST(:session_id AS uuid)
          AND lower(trim(coalesce(dm.drill_name, ''))) NOT IN ('entire session', 'entire session - live')
        ORDER BY dm.primary_label NULLS FIRST, dm.drill_name, dm.id
    """), {"session_id": session_id, "player_id": player_id}).mappings()
    result = []
    for row in rows:
        imported = row["imported_metrics"] or {}
        manual = row["manual_metrics"] or {}
        result.append({
            "id": str(row["id"]),
            "drill_name": row["drill_name"],
            "primary_label": row["primary_label"],
            "secondary_label": row["secondary_label"],
            "tertiary_label": row["tertiary_label"],
            "session_type": row["session_type"],
            "has_imported_data": bool(row["imported_metrics"]),
            "values": {metric: manual.get(metric, _editor_value(imported, metric)) for metric in EDITOR_METRICS},
        })
    return result


def _validate_editor_metrics(metrics: dict[str, float | None]) -> dict[str, float | None]:
    unknown = set(metrics) - set(EDITOR_METRICS)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unsupported metrics: {', '.join(sorted(unknown))}")
    return {key: (None if value is None else float(value)) for key, value in metrics.items()}


def _save_manual_values(connection: Any, update: ManualMetricsUpdate) -> None:
    metrics = _validate_editor_metrics(update.metrics)
    metadata = connection.execute(text("""
        SELECT id FROM drill_metadata
        WHERE id = CAST(:drill_metadata_id AS uuid)
          AND session_id = CAST(:session_id AS uuid)
          AND lower(trim(coalesce(drill_name, ''))) NOT IN ('entire session', 'entire session - live')
    """), update.model_dump()).first()
    player = connection.execute(text("SELECT id, player_details FROM players WHERE id = CAST(:player_id AS uuid)"), update.model_dump()).mappings().first()
    if not metadata or not player:
        raise HTTPException(status_code=404, detail="Session drill or player not found")

    existing_manual = connection.execute(text("""
        SELECT metric_values FROM manual_drill_values
        WHERE session_id = CAST(:session_id AS uuid)
          AND player_id = CAST(:player_id AS uuid)
          AND drill_metadata_id = CAST(:drill_metadata_id AS uuid)
    """), update.model_dump()).scalar_one_or_none() or {}
    merged_metrics = {key: value for key, value in existing_manual.items() if key not in metrics}
    merged_metrics.update({key: value for key, value in metrics.items() if value is not None})
    if not merged_metrics:
        connection.execute(text("""
            DELETE FROM manual_drill_values
            WHERE session_id = CAST(:session_id AS uuid)
              AND player_id = CAST(:player_id AS uuid)
              AND drill_metadata_id = CAST(:drill_metadata_id AS uuid)
        """), update.model_dump())
        return

    participation = connection.execute(text("""
        SELECT id FROM session_players
        WHERE session_id = CAST(:session_id AS uuid) AND player_id = CAST(:player_id AS uuid)
    """), update.model_dump()).first()
    if not participation:
        participation_id = str(uuid4())
        connection.execute(text("""
            INSERT INTO session_players (id, session_id, player_id, source_id, player_details)
            VALUES (CAST(:id AS uuid), CAST(:session_id AS uuid), CAST(:player_id AS uuid),
                    CAST(:source_id AS uuid), CAST(:player_details AS jsonb))
        """), {**update.model_dump(), "id": participation_id, "source_id": str(uuid4()), "player_details": json.dumps({"manual_only": True})})
    else:
        participation_id = str(participation[0])

    existing_drill = connection.execute(text("""
        SELECT id FROM drills
        WHERE session_player_id = CAST(:session_player_id AS uuid)
          AND drill_metadata_id = CAST(:drill_metadata_id AS uuid)
        LIMIT 1
    """), {"session_player_id": participation_id, "drill_metadata_id": update.drill_metadata_id}).first()
    if not existing_drill:
        connection.execute(text("""
            INSERT INTO drills (id, session_player_id, drill_metadata_id, source_id, metrics, raw_data)
            VALUES (CAST(:id AS uuid), CAST(:session_player_id AS uuid), CAST(:drill_metadata_id AS uuid),
                    CAST(:source_id AS uuid), '{}'::jsonb, '{}'::jsonb)
        """), {"id": str(uuid4()), "session_player_id": participation_id, "drill_metadata_id": update.drill_metadata_id, "source_id": str(uuid4())})

    connection.execute(text("""
        INSERT INTO manual_drill_values (id, session_id, player_id, drill_metadata_id, metric_values)
        VALUES (CAST(:id AS uuid), CAST(:session_id AS uuid), CAST(:player_id AS uuid),
                CAST(:drill_metadata_id AS uuid), CAST(:metric_values AS jsonb))
        ON CONFLICT (session_id, player_id, drill_metadata_id)
        DO UPDATE SET metric_values = EXCLUDED.metric_values,
                      updated_at = now()
        """), {**update.model_dump(), "id": str(uuid4()), "metric_values": json.dumps(merged_metrics)})


def _cleanup_empty_manual_player(connection: Any, session_id: str, player_id: str) -> None:
    params = {"session_id": session_id, "player_id": player_id}
    connection.execute(text("""
        DELETE FROM manual_drill_values
        WHERE session_id = CAST(:session_id AS uuid)
          AND player_id = CAST(:player_id AS uuid)
          AND NOT EXISTS (
              SELECT 1
              FROM manual_drill_values remaining
              WHERE remaining.session_id = manual_drill_values.session_id
                AND remaining.player_id = manual_drill_values.player_id
                AND COALESCE(remaining.metric_values, '{}'::jsonb) <> '{}'::jsonb
          )
    """), params)
    connection.execute(text("""
        DELETE FROM drills d
        USING session_players sp
        WHERE d.session_player_id = sp.id
          AND sp.session_id = CAST(:session_id AS uuid)
          AND sp.player_id = CAST(:player_id AS uuid)
          AND (sp.player_details @> '{"manual_only": true}'::jsonb OR COALESCE(sp.player_details, '{}'::jsonb) = '{}'::jsonb)
          AND COALESCE(d.metrics, '{}'::jsonb) = '{}'::jsonb
          AND COALESCE(d.raw_data, '{}'::jsonb) = '{}'::jsonb
    """), params)
    connection.execute(text("""
        DELETE FROM session_players sp
        WHERE sp.session_id = CAST(:session_id AS uuid)
          AND sp.player_id = CAST(:player_id AS uuid)
          AND (sp.player_details @> '{"manual_only": true}'::jsonb OR COALESCE(sp.player_details, '{}'::jsonb) = '{}'::jsonb)
          AND NOT EXISTS (
              SELECT 1 FROM manual_drill_values mdv
              WHERE mdv.session_id = sp.session_id AND mdv.player_id = sp.player_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM drills d
              WHERE d.session_player_id = sp.id
                AND (COALESCE(d.metrics, '{}'::jsonb) <> '{}'::jsonb OR COALESCE(d.raw_data, '{}'::jsonb) <> '{}'::jsonb)
          )
    """), params)


@router.get("/editor/catalog")
def get_editor_catalog(session_id: str, player_id: str) -> dict[str, Any]:
    with get_physical_engine().connect() as connection:
        session = connection.execute(text("""
            SELECT id, activity_id, activity_name, session_date, squad_id
            FROM sessions WHERE id = CAST(:session_id AS uuid)
        """), {"session_id": session_id}).mappings().first()
        player = connection.execute(text("""
            SELECT id, display_name, first_name, last_name, primary_position, secondary_position
            FROM players WHERE id = CAST(:player_id AS uuid)
        """), {"player_id": player_id}).mappings().first()
        if not session or not player:
            raise HTTPException(status_code=404, detail="Session or player not found")
        return {"session": dict(session), "player": dict(player), "metrics": list(EDITOR_METRICS), "drills": _editor_rows(connection, session_id, player_id)}


@router.put("/editor/values")
def update_editor_values(update: ManualMetricsUpdate) -> dict[str, Any]:
    with get_physical_engine().begin() as connection:
        _save_manual_values(connection, update)
    return {"status": "saved", "drill_metadata_id": update.drill_metadata_id, "metrics": update.metrics}


@router.post("/editor/save")
def save_editor_values(update: ManualEditorSave) -> dict[str, Any]:
    with get_physical_engine().begin() as connection:
        for row in update.rows:
            _save_manual_values(connection, ManualMetricsUpdate(
                session_id=update.session_id,
                player_id=update.player_id,
                drill_metadata_id=row.drill_metadata_id,
                metrics=row.metrics,
            ))
        _cleanup_empty_manual_player(connection, update.session_id, update.player_id)
    return {"status": "saved", "updated": len(update.rows)}


@router.post("/editor/bulk")
def bulk_editor_values(update: ManualBulkUpdate) -> dict[str, Any]:
    if update.action not in {"copy", "average"}:
        raise HTTPException(status_code=422, detail="action must be copy or average")
    with get_physical_engine().begin() as connection:
        if update.action == "copy":
            if not update.source_player_id or update.source_player_id == update.player_id:
                raise HTTPException(status_code=422, detail="A different source player is required")
            source_rows = {row["id"]: row for row in _editor_rows(connection, update.session_id, update.source_player_id)}
            source_values = {metadata_id: source_rows[metadata_id]["values"] for metadata_id in update.drill_metadata_ids if metadata_id in source_rows}
        else:
            players = connection.execute(text("SELECT player_id FROM session_players WHERE session_id = CAST(:session_id AS uuid)"), {"session_id": update.session_id}).all()
            all_rows = [_editor_rows(connection, update.session_id, str(row[0])) for row in players]
            source_values = {}
            for metadata_id in update.drill_metadata_ids:
                values = [row["values"] for rows in all_rows for row in rows if row["id"] == metadata_id]
                source_values[metadata_id] = {metric: (sum(float(value[metric]) for value in values if value.get(metric) is not None) / len([value for value in values if value.get(metric) is not None]) if any(value.get(metric) is not None for value in values) else None) for metric in EDITOR_METRICS}
        if update.persist:
            for metadata_id, metrics in source_values.items():
                _save_manual_values(connection, ManualMetricsUpdate(session_id=update.session_id, player_id=update.player_id, drill_metadata_id=metadata_id, metrics=metrics))
    return {"status": "saved" if update.persist else "prepared", "updated": len(source_values), "action": update.action, "rows": [{"drill_metadata_id": metadata_id, "metrics": metrics} for metadata_id, metrics in source_values.items()]}