"""Controlled STATSports API discovery workflow."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .client import StatsportAPIClient, StatsportAPIError
from .config import StatsportSettings


def load_project_environment() -> None:
    """Load the ignored shared environment file for local diagnostics."""
    project_root = Path(__file__).resolve().parents[4]
    load_dotenv(project_root / "config" / ".env", override=False)


def summarize_activity(payload: Any) -> dict[str, Any]:
    """Return structural information without exposing player or KPI values."""
    if isinstance(payload, list):
        activities = [item for item in payload if isinstance(item, dict)]
        session_players = [
            player
            for activity in activities
            for player in (activity.get("sessionPlayers") or [])
            if isinstance(player, dict)
        ]
        drills = [
            drill
            for player in session_players
            for drill in (player.get("drills") or [])
            if isinstance(drill, dict)
        ]
        return {
            "payload_type": "list",
            "activity_count": len(activities),
            "session_details_present": all(
                isinstance(activity.get("sessionDetails"), dict)
                for activity in activities
            ),
            "session_player_count": len(session_players),
            "drill_count": len(drills),
        }

    if not isinstance(payload, dict):
        return {"payload_type": type(payload).__name__}

    players = payload.get("players") or payload.get("sessionPlayers") or []
    drill_count = sum(
        len(player.get("drills") or [])
        for player in players
        if isinstance(player, dict)
    )
    return {
        "payload_type": "object",
        "top_level_keys": sorted(payload.keys()),
        "activity_id_present": bool(payload.get("id")),
        "session_present": isinstance(payload.get("session"), dict),
        "player_count": len(players) if isinstance(players, list) else None,
        "drill_count": drill_count,
    }


async def collect_diagnostics(
    third_party_api_id: str | None,
    share_date: str | None = None,
    output_path: Path | None = None,
    settings: StatsportSettings | None = None,
) -> dict[str, Any]:
    """Call discovery endpoints and optionally save the full-session payload."""
    async with StatsportAPIClient(settings=settings) as client:
        result: dict[str, Any] = {
            "test": await client.test(),
            "available_metrics": await client.get_available_metrics(),
        }
        if not third_party_api_id:
            result["full_session_skipped"] = "thirdPartyApiId is required for session data"
            return result

        full_session = await client.get_full_session_by_share_date(
            third_party_api_id,
            share_date,
        )
        result["full_session_summary"] = summarize_activity(full_session)

        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(full_session, indent=2, ensure_ascii=True),
                encoding="utf-8",
            )
            result["full_session_output"] = str(output_path)

        return result


def main() -> int:
    load_project_environment()
    parser = argparse.ArgumentParser(description="Discover the STATSports V7 response shape")
    parser.add_argument(
        "--api-id",
        default=(
            os.getenv("STATSPORT_API_ID")
            or os.getenv("STATSPORT_THIRD_PARTY_API_ID")
            or os.getenv("STATSPORT_API_TOKEN")
        ),
        help="STATSports thirdPartyApiId (defaults to the configured token)",
    )
    parser.add_argument("--share-date", help="ISO date or datetime used by getFullSessionByShareDate")
    parser.add_argument("--output", type=Path, help="Optional path for the raw full-session JSON")
    args = parser.parse_args()
    try:
        result = asyncio.run(
            collect_diagnostics(
                third_party_api_id=args.api_id,
                share_date=args.share_date,
                output_path=args.output,
            )
        )
    except StatsportAPIError as exc:
        parser.error(str(exc))

    print(json.dumps(result, indent=2, ensure_ascii=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
