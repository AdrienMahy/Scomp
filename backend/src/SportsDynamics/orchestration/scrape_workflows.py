"""Coordination workflows for the five public SportsDynamics scrape operations."""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import Game
from .scraper_coordinator import ScraperCoordinator
from .task_tracker import TaskTracker


async def _enrich_players(
    db: Session,
    competition_id: str,
    season_id: str,
    game_ids: List[str],
) -> Dict[str, Any]:
    if not game_ids:
        return {"status": "skipped", "message": "No games were processed"}
    from src.SportsDynamics.api.routes.players import enrich_players_for_games

    return await enrich_players_for_games(
        db=db,
        competition_id=competition_id,
        season_id=season_id,
        game_ids=game_ids,
    )


async def enrich_players(
    db: Session,
    competition_id: str,
    season_id: str,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run standalone player enrichment under the shared task lifecycle."""
    tracker = TaskTracker(db, "SportsDynamics", "player_enrichment", competition_id, season_id, task_id=task_id)
    tracker.start()
    try:
        tracker.phase("player_enrichment", "Enriching players from season lineups")
        result = await _enrich_players(
            db,
            competition_id,
            season_id,
            [game.id for game in db.query(Game).filter(
                Game.competition_id == competition_id,
                Game.season_id == season_id,
            ).all()],
        )
        tracker.finish("completed" if result.get("status") != "error" else "partial", result.get("message"))
        return {"task_id": tracker.id, "enrichment": result}
    except Exception as exc:
        tracker.fail(str(exc))
        raise


async def initialize_season(
    db: Session,
    competition_id: str,
    season_id: str,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronize the season schedule, then synchronize teams."""
    tracker = TaskTracker(db, "SportsDynamics", "season_initialization", competition_id, season_id, task_id=task_id)
    tracker.start()
    tracker.phase("schedule", "Fetching and persisting season schedule")
    coordinator = ScraperCoordinator(task_id=tracker.id)
    filters = {
        "available": True,
        "competition_id": competition_id,
        "season_id": season_id,
        "season_name": str(season_id),
    }
    games = []
    page = 1
    limit = 380

    while True:
        page_games = await coordinator.scrape_games_basic(filters, limit=limit, page=page)
        if not page_games:
            break
        games.extend(page_games)
        if len(page_games) < limit:
            break
        page += 1

    from src.SportsDynamics.api.routes.teams import enrich_teams_from_api

    teams_result = await enrich_teams_from_api(
        db,
        competition_id=competition_id,
        season_id=season_id,
    )
    tracker.progress(processed=len(games), message=f"Schedule persisted: {len(games)} games")
    tracker.phase("team_enrichment", "Synchronizing teams")
    tracker.finish("completed", "Season initialization completed")
    return {
        "status": "completed",
        "task_id": tracker.id,
        "competition_id": competition_id,
        "season_id": season_id,
        "games_count": len(games),
        "teams": teams_result,
    }


async def _available_games_for_round(
    coordinator: ScraperCoordinator,
    competition_id: str,
    season_id: str,
    round_name: str,
) -> List[Dict[str, Any]]:
    return coordinator.provider.fetch_games(
        {
            "available": True,
            "competition_id": competition_id,
            "season_id": season_id,
            "round": [round_name],
        },
        limit=380,
        page=1,
    )


async def scrape_round(
    db: Session,
    competition_id: str,
    season_id: str,
    round_name: str,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Clear and reprocess all available games in one round."""
    tracker = TaskTracker(db, "SportsDynamics", "round_scrape", competition_id, season_id, round_name, task_id=task_id)
    tracker.start()
    try:
        tracker.phase("api_fetch", f"Fetching available games for round {round_name}")
        coordinator = ScraperCoordinator(task_id=tracker.id)
        raw_games = await _available_games_for_round(coordinator, competition_id, season_id, round_name)
        game_ids = [game.get("id") for game in raw_games if game.get("id")]
        tracker.task.total_items = len(game_ids)
        tracker._commit()
        tracker.phase("game_processing", f"Parsing and persisting round {round_name}")
        result = await coordinator.scrape_available_files(
            {"available": True, "competition_id": competition_id, "season_id": season_id, "round": [round_name]},
            limit=380,
            page=1,
            progress_callback=lambda processed, failed, skipped, current_item_id: tracker.progress(
                processed=processed + failed + skipped,
                failed=failed,
                current_item_id=current_item_id,
                message=f"Round progress: {processed + failed + skipped}/{len(game_ids)} games",
            ),
            cancellation_callback=tracker.cancellation_requested,
        )
        processed = result.get("processed_count", 0)
        failed = result.get("error_count", 0)
        skipped = result.get("skipped_count", 0)
        tracker.progress(
            processed=processed + failed + skipped,
            failed=failed,
            message=f"Round processed: {processed} games, {failed} errors, {skipped} skipped",
        )
        if result.get("cancelled"):
            tracker.cancel()
            return {
                "status": "cancelled",
                "task_id": tracker.id,
                "competition_id": competition_id,
                "season_id": season_id,
                "round": round_name,
                "game_ids": game_ids,
                "scrape": result,
            }
        tracker.phase("player_enrichment", "Enriching players from processed lineups")
        enrichment = await _enrich_players(db, competition_id, season_id, game_ids) if processed else {"status": "skipped"}
        status = "completed" if failed == 0 else "partial"
        tracker.finish(status, f"Round completed with {failed} errors")
    except Exception as exc:
        tracker.fail(str(exc))
        raise
    return {
        "status": status,
        "task_id": tracker.id,
        "competition_id": competition_id,
        "season_id": season_id,
        "round": round_name,
        "game_ids": game_ids,
        "scrape": result,
        "enrichment": enrichment,
    }


async def scrape_game(db: Session, game_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
    """Clear and reprocess one available game, keeping the Game row."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise ValueError(f"Game not found: {game_id}")
    if not game.round_name:
        raise ValueError(f"Game has no round: {game_id}")

    tracker = TaskTracker(db, "SportsDynamics", "game_scrape", str(game.competition_id), str(game.season_id), game.round_name, task_id=task_id)
    tracker.start(total_items=1)
    tracker.phase("api_fetch", "Checking game availability in SportsDynamics")
    coordinator = ScraperCoordinator(task_id=tracker.id)
    raw_games = await _available_games_for_round(
        coordinator, game.competition_id, str(game.season_id), game.round_name
    )
    matching = [raw for raw in raw_games if raw.get("id") == game_id]
    if not matching:
        tracker.finish("skipped", "Game is not currently available in SportsDynamics")
        return {
            "status": "skipped",
            "task_id": tracker.id,
            "game_id": game_id,
            "message": "Game is not currently available in SportsDynamics",
        }

    tracker.phase("game_processing", "Parsing and persisting match data")
    scraped = await coordinator.scrape_games(
        {
            "available": True,
            "competition_id": game.competition_id,
            "season_id": str(game.season_id),
            "round": [game.round_name],
        },
        limit=380,
        page=1,
        game_id_filter=game_id,
    )
    enrichment = await _enrich_players(db, game.competition_id, str(game.season_id), [game_id]) if scraped else {"status": "skipped"}
    tracker.progress(processed=1 if scraped else 0, failed=0 if scraped else 1, current_item_id=game_id)
    tracker.finish("completed" if scraped else "failed", "Game processing completed" if scraped else "Game processing returned no data")
    return {
        "status": "success" if scraped else "error",
        "task_id": tracker.id,
        "game_id": game_id,
        "scraped": bool(scraped),
        "enrichment": enrichment,
    }


async def scrape_autonomous(
    db: Session,
    competition_id: str,
    season_id: str,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Detect new or changed available games, then process only those games."""
    tracker = TaskTracker(db, "SportsDynamics", "autonomous_scrape", competition_id, season_id, task_id=task_id)
    tracker.start()
    tracker.phase("change_detection", "Comparing SportsDynamics games with the database")
    coordinator = ScraperCoordinator(task_id=tracker.id)
    filters = {
        "available": True,
        "competition_id": competition_id,
        "season_id": season_id,
    }
    raw_games = coordinator.provider.fetch_games(filters, limit=380, page=1)
    changed_ids = _find_changed_game_ids(db, coordinator, raw_games)
    changed_games = [
        raw_game for raw_game in raw_games if raw_game.get("id") in changed_ids
    ]
    reason_counts: Dict[str, int] = {}
    affected_matches = []
    for raw_game in changed_games:
        reasons = coordinator._get_game_changes(raw_game["id"], raw_game)
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        round_data = raw_game.get("round") or {}
        affected_matches.append({
            "id": raw_game["id"],
            "name": raw_game.get("name"),
            "round": round_data.get("name") if isinstance(round_data, dict) else round_data,
            "change_reasons": reasons,
        })

    tracker.task.extra_metadata = {
        **(tracker.task.extra_metadata or {}),
        "change_detection": {
            "provider_games_count": len(raw_games),
            "affected_games_count": len(changed_games),
            "reason_counts": reason_counts,
            "affected_matches": affected_matches,
        },
    }
    tracker._commit()
    reason_summary = ", ".join(
        f"{count} {reason}" for reason, count in sorted(reason_counts.items())
    ) or "no changes"
    tracker.phase(
        "change_detection",
        f"Detected {len(changed_games)} affected games ({reason_summary})",
    )

    processed = []
    for game_id in changed_ids:
        raw_game = next(item for item in raw_games if item.get("id") == game_id)
        round_name = (raw_game.get("round") or {}).get("name")
        if not round_name:
            continue
        games = await coordinator.scrape_games(
            {
                "available": True,
                "competition_id": competition_id,
                "season_id": season_id,
                "round": [round_name],
            },
            limit=380,
            page=1,
            game_id_filter=game_id,
        )
        if games:
            processed.append(game_id)

    tracker.progress(processed=len(processed), failed=len(changed_ids) - len(processed))
    tracker.phase("player_enrichment", "Enriching players from changed games")
    enrichment = await _enrich_players(db, competition_id, season_id, processed)
    status = "completed" if len(processed) == len(changed_ids) else "partial"
    tracker.finish(status, f"Autonomous scrape processed {len(processed)} games")

    return {
        "status": status,
        "task_id": tracker.id,
        "competition_id": competition_id,
        "season_id": season_id,
        "detected_count": len(changed_ids),
        "processed_count": len(processed),
        "processed_game_ids": processed,
        "enrichment": enrichment,
    }


def _find_changed_game_ids(
    db: Session,
    coordinator: ScraperCoordinator,
    raw_games: List[Dict[str, Any]],
) -> List[str]:
    """Return provider games that are new or have changed tracked state."""
    changed_ids: List[str] = []
    for raw_game in raw_games:
        game_id = raw_game.get("id")
        if not game_id:
            continue
        existing = db.query(Game).filter(Game.id == game_id).first()
        if existing is None or coordinator._should_update_game(game_id, raw_game):
            changed_ids.append(game_id)
    return changed_ids


def autonomous_dry_run(
    db: Session,
    competition_id: str,
    season_id: str,
) -> Dict[str, Any]:
    """Inspect an autonomous run without deleting or persisting any data."""
    coordinator = ScraperCoordinator()
    try:
        raw_games = coordinator.provider.fetch_games(
            {
                "available": True,
                "competition_id": competition_id,
                "season_id": season_id,
            },
            limit=380,
            page=1,
        )
        changed_ids = set(_find_changed_game_ids(db, coordinator, raw_games))
        matches = []
        for raw_game in raw_games:
            game_id = raw_game.get("id")
            if game_id not in changed_ids:
                continue
            round_data = raw_game.get("round") or {}
            matches.append({
                "id": game_id,
                "name": raw_game.get("name"),
                "round": round_data.get("name") if isinstance(round_data, dict) else round_data,
                "starts_at": raw_game.get("startsAt"),
                "available": raw_game.get("available"),
                "is_ugd_available": raw_game.get("isUGDAvailable"),
                "rgd_status": raw_game.get("rgdStatus"),
                "ugd_status": raw_game.get("ugdStatus"),
                "has_output_files": bool((raw_game.get("outputFiles") or {}).get("items")),
                "is_new": db.query(Game).filter(Game.id == game_id).first() is None,
                "change_reasons": coordinator._get_game_changes(game_id, raw_game),
            })
        return {
            "status": "dry_run",
            "competition_id": competition_id,
            "season_id": season_id,
            "provider_games_count": len(raw_games),
            "affected_games_count": len(matches),
            "games": matches,
            "message": "No data was deleted, downloaded, or persisted.",
        }
    finally:
        coordinator.close()
