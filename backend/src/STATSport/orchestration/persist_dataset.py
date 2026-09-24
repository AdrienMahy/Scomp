"""Persist an exported STATSports dataset into the PhysicalData database."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from sqlalchemy import create_engine, text


def physical_database_url(config_path: Path) -> str:
    """Read the explicit PhysicalData URL from the shared configuration."""
    configured_url = os.getenv("PHYSICAL_DATABASE_URL")
    if configured_url:
        return configured_url

    values = dotenv_values(config_path)
    configured_url = values.get("PHYSICAL_DATABASE_URL")
    if not configured_url:
        raise ValueError("PHYSICAL_DATABASE_URL is required")
    return configured_url


def json_value(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=True)


def same_timestamp(left: Any, right: Any) -> bool:
    def parse(value: Any) -> datetime:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    return parse(left).astimezone(timezone.utc) == parse(right).astimezone(timezone.utc)


class ActivityQualityError(ValueError):
    """Raised when too many activity players have no usable distance metric."""


def find_existing_activity(connection: Any, session: dict[str, Any]) -> Any:
    """Lock and return the stored activity before any related row is written."""
    return connection.execute(
        text("""
            SELECT id, share_date, response_hash
            FROM sessions
            WHERE activity_id = CAST(:activity_id AS uuid)
            FOR UPDATE
        """),
        {"activity_id": session["activity_id"]},
    ).mappings().first()


def activity_is_unchanged(existing: Any, session: dict[str, Any]) -> bool:
    """Return whether the incoming activity is already persisted unchanged."""
    return bool(
        existing
        and same_timestamp(existing["share_date"], session["share_date"])
        and existing["response_hash"] == session["response_hash"]
    )


def invalid_distance_players(
    tables: dict[str, list[dict[str, Any]]],
    session: dict[str, Any],
) -> list[dict[str, Any]]:
    activity_players = [
        row for row in tables["session_players"]
        if row["session_id"] == session["id"]
    ]
    invalid: list[dict[str, Any]] = []
    drills_by_player: dict[str, list[dict[str, Any]]] = {}
    for drill in tables["drills"]:
        drills_by_player.setdefault(drill["session_player_id"], []).append(drill)

    players_by_id = {player["id"]: player for player in tables["players"]}
    for activity_player in activity_players:
        distances: list[Any] = []
        for drill in drills_by_player.get(activity_player["id"], []):
            if (drill.get("raw_data") or {}).get("drillName") != "Entire Session":
                continue
            metrics = drill.get("metrics") or {}
            distance = (metrics.get("distance") or {}).get("distanceTotal")
            distances.append(distance)
        if any(isinstance(distance, (int, float)) and distance > 0 for distance in distances):
            continue
        player = players_by_id.get(activity_player["player_id"], {})
        invalid.append({
            "player_id": activity_player["player_id"],
            "source_id": activity_player.get("source_id"),
            "display_name": player.get("display_name"),
            "distanceTotal": distances[0] if distances else None,
        })
    return invalid


def import_activity(connection: Any, tables: dict[str, list[dict[str, Any]]], session: dict[str, Any], counts: dict[str, int]) -> None:
    """Import one activity and all of its related rows in one transaction."""
    existing = find_existing_activity(connection, session)
    if activity_is_unchanged(existing, session):
        counts["skipped"] += 1
        return

    invalid_players = invalid_distance_players(tables, session)
    if len(invalid_players) > 2:
        raise ActivityQualityError(
            f"Activity rejected: {len(invalid_players)} players have missing or non-positive distanceTotal; "
            f"maximum allowed is 2. Details: {json.dumps(invalid_players, ensure_ascii=True)}"
        )

    for squad in tables["squads"]:
        if squad["id"] != session["squad_id"]:
            continue
        connection.execute(
            text("""
                INSERT INTO squads (id, external_id, name, raw_data)
                VALUES (CAST(:id AS uuid), CAST(:external_id AS uuid), :name, CAST(:raw_data AS jsonb))
                ON CONFLICT (external_id) DO UPDATE SET name = EXCLUDED.name, raw_data = EXCLUDED.raw_data
            """),
            {**squad, "raw_data": json_value(squad["raw_data"])},
        )

    activity_players = [row for row in tables["session_players"] if row["session_id"] == session["id"]]
    player_ids = {row["player_id"] for row in activity_players}
    for player in tables["players"]:
        if player["id"] not in player_ids:
            continue
        connection.execute(
            text("""
                INSERT INTO players (
                    id, identity_key, display_name, first_name, last_name,
                    primary_position, secondary_position, active_squad_name, player_details
                ) VALUES (
                    CAST(:id AS uuid), :identity_key, :display_name, :first_name, :last_name,
                    :primary_position, :secondary_position, :active_squad_name, CAST(:player_details AS jsonb)
                )
                ON CONFLICT (identity_key) DO UPDATE SET
                    display_name = EXCLUDED.display_name, first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name, primary_position = EXCLUDED.primary_position,
                    secondary_position = EXCLUDED.secondary_position, active_squad_name = EXCLUDED.active_squad_name,
                    player_details = EXCLUDED.player_details, updated_at = now()
            """),
            {**player, "player_details": json_value(player["player_details"])},
        )

    if existing:
        connection.execute(text("DELETE FROM session_players WHERE session_id = CAST(:id AS uuid)"), {"id": existing["id"]})
        connection.execute(text("DELETE FROM drill_metadata WHERE session_id = CAST(:id AS uuid)"), {"id": existing["id"]})
        connection.execute(
            text("""
                UPDATE sessions SET activity_name = :activity_name, share_date = CAST(:share_date AS timestamptz),
                    squad_id = CAST(:squad_id AS uuid), season_id = (
                        SELECT id FROM seasons
                        WHERE CAST(:session_date AS timestamptz)::date >= start_date
                          AND CAST(:session_date AS timestamptz)::date < end_date
                    ), session_date = CAST(:session_date AS timestamptz),
                    start_time = CAST(:start_time AS timestamptz), end_time = CAST(:end_time AS timestamptz),
                    session_type = :session_type, raw_data = CAST(:raw_data AS jsonb), response_hash = :response_hash,
                    version = version + 1, updated_at = now()
                WHERE id = CAST(:id AS uuid)
            """),
            {**session, "id": existing["id"], "raw_data": json_value(session["raw_data"])},
        )
        session_id = str(existing["id"])
        counts["updated"] += 1
    else:
        connection.execute(
            text("""
                INSERT INTO sessions (
                    id, activity_id, activity_name, share_date, squad_id, season_id, session_date,
                    start_time, end_time, session_type, raw_data, response_hash, version
                ) VALUES (
                    CAST(:id AS uuid), CAST(:activity_id AS uuid), :activity_name,
                                        CAST(:share_date AS timestamptz), CAST(:squad_id AS uuid), (
                                                SELECT id FROM seasons
                                                WHERE CAST(:session_date AS timestamptz)::date >= start_date
                                                    AND CAST(:session_date AS timestamptz)::date < end_date
                                        ), CAST(:session_date AS timestamptz),
                    CAST(:start_time AS timestamptz), CAST(:end_time AS timestamptz), :session_type,
                    CAST(:raw_data AS jsonb), :response_hash, :version
                )
            """),
            {**session, "raw_data": json_value(session["raw_data"])},
        )
        session_id = session["id"]
        counts["inserted"] += 1

    metadata = [row for row in tables["drill_metadata"] if row["session_id"] == session["id"]]
    for row in metadata:
        connection.execute(
            text("""
                INSERT INTO drill_metadata (
                    id, session_id, signature, drill_name, primary_label,
                    secondary_label, tertiary_label, session_type
                ) VALUES (
                    CAST(:id AS uuid), CAST(:session_id AS uuid), :signature, :drill_name,
                    :primary_label, :secondary_label, :tertiary_label, :session_type
                )
            """), row,
        )

    activity_player_ids = set()
    for row in activity_players:
        connection.execute(
            text("""
                INSERT INTO session_players (
                    id, session_id, player_id, source_id, raw_data_id, player_details
                ) VALUES (
                    CAST(:id AS uuid), CAST(:session_id AS uuid), CAST(:player_id AS uuid),
                    CAST(:source_id AS uuid), CAST(:raw_data_id AS uuid), CAST(:player_details AS jsonb)
                )
            """),
            {**row, "session_id": session_id, "player_details": json_value(row["player_details"])},
        )
        activity_player_ids.add(row["id"])

    for drill in tables["drills"]:
        if drill["session_player_id"] not in activity_player_ids:
            continue
        connection.execute(
            text("""
                INSERT INTO drills (
                    id, session_player_id, drill_metadata_id, source_id, session_player_data_id,
                    start_time, end_time, free_text, metrics, raw_data
                ) VALUES (
                    CAST(:id AS uuid), CAST(:session_player_id AS uuid), CAST(:drill_metadata_id AS uuid),
                    CAST(:source_id AS uuid), CAST(:session_player_data_id AS uuid), CAST(:start_time AS timestamptz),
                    CAST(:end_time AS timestamptz), :free_text, CAST(:metrics AS jsonb), CAST(:raw_data AS jsonb)
                )
            """),
            {**drill, "metrics": json_value(drill["metrics"]), "raw_data": json_value(drill["raw_data"])},
        )

    snapshot = next(row for row in tables["api_snapshots"] if row["activity_id"] == session["activity_id"])
    connection.execute(
        text("""
            INSERT INTO api_snapshots (
                id, activity_id, endpoint, request_payload, response_payload, http_status, api_version, response_hash
            ) VALUES (
                CAST(:id AS uuid), CAST(:activity_id AS uuid), :endpoint, CAST(:request_payload AS jsonb),
                CAST(:response_payload AS jsonb), :http_status, :api_version, :response_hash
            ) ON CONFLICT (activity_id) DO UPDATE SET endpoint = EXCLUDED.endpoint,
                request_payload = EXCLUDED.request_payload, response_payload = EXCLUDED.response_payload,
                http_status = EXCLUDED.http_status, api_version = EXCLUDED.api_version,
                response_hash = EXCLUDED.response_hash, received_at = now()
        """),
        {**snapshot, "request_payload": json_value(snapshot["request_payload"]), "response_payload": json_value(snapshot["response_payload"])},
    )


def import_dataset(dataset: dict[str, Any], database_url: str, run_id: str | None = None) -> dict[str, Any]:
    """Import each activity independently and continue after activity failures."""
    tables = dataset["tables"]
    counts: dict[str, Any] = {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        for session in tables["sessions"]:
            activity_counts = {"inserted": 0, "updated": 0, "skipped": 0}
            activity_id = session.get("activity_id")
            activity_name = session.get("activity_name") or "Unnamed activity"
            try:
                with engine.begin() as connection:
                    if run_id:
                        from .scrape_logs import write_log
                        write_log(connection, run_id, "INFO", "activity_processing", "Processing activity",
                                  activity_id=activity_id, activity_name=activity_name,
                                  details={"session_date": session.get("session_date")})
                    import_activity(connection, tables, session, activity_counts)
                    if run_id:
                        if activity_counts["skipped"]:
                            write_log(connection, run_id, "INFO", "data_presence",
                                      "Activity already present and unchanged; persistence skipped",
                                      activity_id=activity_id, activity_name=activity_name,
                                      details=activity_counts)
                        else:
                            write_log(connection, run_id, "INFO", "persistence", "Activity persisted",
                                      activity_id=activity_id, activity_name=activity_name, details=activity_counts)
                for key in activity_counts:
                    counts[key] += activity_counts[key]
            except Exception as error:
                counts["failed"] += 1
                counts["errors"].append({"activity_id": activity_id, "error": str(error)})
                if run_id:
                    with engine.begin() as connection:
                        from .scrape_logs import write_log
                        step = "quality_validation" if isinstance(error, ActivityQualityError) else "activity_failed"
                        write_log(connection, run_id, "ERROR", step, str(error),
                                  activity_id=activity_id, activity_name=activity_name)
    finally:
        engine.dispose()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a STATSports PhysicalData JSON export")
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/.env"))
    args = parser.parse_args()
    dataset = json.loads(args.input.read_text(encoding="utf-8"))
    result = import_dataset(dataset, physical_database_url(args.config))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()