"""PhysicalData browsing and STATSports scraping control routes."""

from datetime import date, time
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
            {where_clause}
            ORDER BY s.session_date DESC, s.activity_name
            LIMIT :limit
        """), params).mappings()
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
        return {"run": dict(run), "logs": [dict(log) for log in logs]}


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
                   sp.player_details
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