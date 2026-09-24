"""Build a simplified PhysicalData JSON dataset from STATSports V7."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

NAMESPACE = UUID("f2f4afc7-7f53-4d6a-9e0a-5e8bc4b765d2")

SCHEMA = {
    "squads": {"columns": {"id": "uuid", "external_id": "uuid", "name": "text|null", "raw_data": "jsonb"}, "primary_key": ["id"], "unique": [["external_id"]]},
    "players": {"columns": {"id": "uuid", "identity_key": "text", "display_name": "text|null", "first_name": "text|null", "last_name": "text|null", "primary_position": "text|null", "secondary_position": "text|null", "active_squad_name": "text|null", "player_details": "jsonb", "created_at": "timestamptz", "updated_at": "timestamptz"}, "primary_key": ["id"], "unique": [["identity_key"]]},
    "sessions": {"columns": {"id": "uuid", "activity_id": "uuid", "activity_name": "text|null", "share_date": "timestamptz", "squad_id": "uuid", "session_date": "timestamptz", "start_time": "timestamptz|null", "end_time": "timestamptz|null", "session_type": "text|null", "raw_data": "jsonb", "response_hash": "text", "version": "integer", "created_at": "timestamptz", "updated_at": "timestamptz"}, "primary_key": ["id"], "unique": [["activity_id"]], "foreign_keys": {"squad_id": "squads.id"}},
    "session_players": {"columns": {"id": "uuid", "session_id": "uuid", "player_id": "uuid", "source_id": "uuid", "raw_data_id": "uuid|null", "player_details": "jsonb", "created_at": "timestamptz"}, "primary_key": ["id"], "unique": [["session_id", "player_id"], ["session_id", "source_id"]], "foreign_keys": {"session_id": "sessions.id", "player_id": "players.id"}},
    "drill_metadata": {"columns": {"id": "uuid", "session_id": "uuid", "signature": "text", "drill_name": "text|null", "primary_label": "text|null", "secondary_label": "text|null", "tertiary_label": "text|null", "session_type": "text|null"}, "primary_key": ["id"], "unique": [["session_id", "signature"]], "foreign_keys": {"session_id": "sessions.id"}},
    "drills": {"columns": {"id": "uuid", "session_player_id": "uuid", "drill_metadata_id": "uuid", "source_id": "uuid", "session_player_data_id": "uuid|null", "start_time": "timestamptz|null", "end_time": "timestamptz|null", "free_text": "text|null", "metrics": "jsonb", "raw_data": "jsonb"}, "primary_key": ["id"], "unique": [["session_player_id", "source_id"]], "foreign_keys": {"session_player_id": "session_players.id", "drill_metadata_id": "drill_metadata.id"}},
    "api_snapshots": {"columns": {"id": "uuid", "activity_id": "uuid|null", "endpoint": "text", "request_payload": "jsonb|null", "response_payload": "jsonb", "http_status": "integer", "api_version": "text", "response_hash": "text", "received_at": "timestamptz"}, "primary_key": ["id"], "unique": [["activity_id"]]},
}


def stable_id(value: str) -> str:
    return str(uuid5(NAMESPACE, value))


def iso(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) == 10:
        return text + "T00:00:00Z"
    if not text.endswith("Z") and "+" not in text:
        return text + "Z"
    return text


def _canonicalize(payload: Any, key: str | None = None) -> Any:
    if isinstance(payload, dict):
        ignored_fields = {
            "sessionPlayers": {"id", "rawDataId"},
            "drills": {"id", "sessionPlayerDataId"},
        }.get(key, set())
        return {
            name: _canonicalize(value, name)
            for name, value in payload.items()
            if name not in ignored_fields
        }
    if isinstance(payload, list):
        values = [_canonicalize(value, key) for value in payload]
        if key in {"sessionPlayers", "drills"}:
            return sorted(values, key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")))
        return values
    return payload


def response_hash(payload: Any) -> str:
    canonical_payload = _canonicalize(payload)
    encoded = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def category(code: str) -> str:
    lower = code.lower()
    if "distance" in lower: return "distance"
    if "speed" in lower or "sprint" in lower: return "speed"
    if "accel" in lower: return "acceleration"
    if "decel" in lower: return "deceleration"
    if "heart" in lower or lower.startswith("hr") or "exertion" in lower: return "heart_rate"
    if "metabolic" in lower or lower in {"emd", "energyexpenditure"}: return "metabolic"
    if "load" in lower or lower in {"hmld", "hmltime"}: return "load"
    if "impact" in lower or "collision" in lower: return "impact"
    if "symmetry" in lower or "step" in lower or "dynamic" in lower: return "imu_loads"
    return "sport_specific"


def player_identity(details: dict[str, Any]) -> str:
    fields = {key: details.get(key) for key in ("customPlayerId", "displayName", "firstName", "lastName", "dateOfBirth")}
    return json.dumps(fields, sort_keys=True, ensure_ascii=True)


def build_dataset(payload: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    tables = {name: [] for name in SCHEMA}
    squad_ids: dict[str, str] = {}
    player_ids: dict[str, str] = {}
    metadata_ids: dict[tuple[str, str], str] = {}
    for activity in payload:
        activity_digest = response_hash(activity)
        details = activity.get("sessionDetails") or {}
        squad_external_id = details.get("squadId")
        squad_key = str(squad_external_id) if squad_external_id else "unknown"
        squad_external_value = squad_external_id or stable_id("external-squad:unknown")
        squad_id = squad_ids.setdefault(squad_key, stable_id(f"squad:{squad_key}"))
        if not any(row["id"] == squad_id for row in tables["squads"]):
            tables["squads"].append({"id": squad_id, "external_id": squad_external_value,
                                      "name": "Unknown squad" if not squad_external_id else None,
                                      "raw_data": {"squadId": squad_external_id}})

        activity_id = activity.get("id")
        session_id = stable_id(f"activity:{activity_id}")
        tables["sessions"].append({"id": session_id, "activity_id": activity_id, "activity_name": activity.get("sessionName"), "share_date": iso(activity.get("shareDate")), "squad_id": squad_id, "session_date": iso(details.get("sessionDate")), "start_time": iso(details.get("startTime")), "end_time": iso(details.get("endTime")), "session_type": details.get("sessionType"), "raw_data": activity, "response_hash": activity_digest, "version": 1, "created_at": now, "updated_at": now})

        for session_player in activity.get("sessionPlayers") or []:
            details_player = session_player.get("playerDetails") or {}
            identity_key = player_identity(details_player)
            player_id = player_ids.setdefault(identity_key, stable_id("player:" + identity_key))
            if not any(row["id"] == player_id for row in tables["players"]):
                tables["players"].append({"id": player_id, "identity_key": identity_key, "display_name": details_player.get("displayName"), "first_name": details_player.get("firstName"), "last_name": details_player.get("lastName"), "primary_position": details_player.get("primaryPosition"), "secondary_position": details_player.get("secondaryPosition"), "active_squad_name": details_player.get("activeSquadName"), "player_details": details_player, "created_at": now, "updated_at": now})
            session_player_id = stable_id(f"session-player:{session_id}:{session_player.get('id')}")
            tables["session_players"].append({"id": session_player_id, "session_id": session_id, "player_id": player_id, "source_id": session_player.get("id"), "raw_data_id": session_player.get("rawDataId"), "player_details": details_player, "created_at": now})

            for drill in session_player.get("drills") or []:
                signature = "|".join(str(drill.get(key) or "") for key in ("sessionType", "drillName", "primaryLabel", "secondaryLabel", "tertiaryLabel"))
                metadata_key = (session_id, signature)
                metadata_id = metadata_ids.setdefault(metadata_key, stable_id(f"drill-metadata:{session_id}:{signature}"))
                if not any(row["id"] == metadata_id for row in tables["drill_metadata"]):
                    tables["drill_metadata"].append({"id": metadata_id, "session_id": session_id, "signature": signature, "drill_name": drill.get("drillName"), "primary_label": drill.get("primaryLabel"), "secondary_label": drill.get("secondaryLabel"), "tertiary_label": drill.get("tertiaryLabel"), "session_type": drill.get("sessionType")})
                grouped_metrics: dict[str, dict[str, Any]] = {}
                for code, value in (drill.get("drillKpi") or {}).items():
                    grouped_metrics.setdefault(category(code), {})[code] = value
                tables["drills"].append({"id": stable_id(f"drill:{session_player_id}:{drill.get('id')}"), "session_player_id": session_player_id, "drill_metadata_id": metadata_id, "source_id": drill.get("id"), "session_player_data_id": drill.get("sessionPlayerDataId"), "start_time": iso(drill.get("startTime")), "end_time": iso(drill.get("endTime")), "free_text": drill.get("freeText"), "metrics": grouped_metrics, "raw_data": drill})

        tables["api_snapshots"].append({"id": stable_id("snapshot:" + str(activity_id)), "activity_id": activity_id, "endpoint": "getFullSessionByShareDate", "request_payload": {"shareDate": activity.get("shareDate")}, "response_payload": activity, "http_status": 200, "api_version": "7", "response_hash": activity_digest, "received_at": now})
    return {"metadata": {"name": "STATSport PhysicalData JSON dataset", "source_file": "start/STATSport/full_session_2026-09-22.json", "generated_at": now, "api": "STATSports Third Party API V7", "sensitive_data": True}, "schema": SCHEMA, "counts": {name: len(rows) for name, rows in tables.items()}, "tables": tables}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Expected a list of STATSports activities")
    dataset = build_dataset(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(dataset["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
