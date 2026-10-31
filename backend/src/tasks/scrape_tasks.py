"""Celery scraping tasks"""
from datetime import datetime, timedelta, timezone
import asyncio
import logging
import os
from typing import List, Optional
from zoneinfo import ZoneInfo

import redis
from sqlalchemy import text

from .celery_config import app
from ..config.database import SessionLocal
from ..SportsDynamics.models import Game, ScrapingLog, ScrapingTask, TaskStatus
from ..SportsDynamics.automation import SmartScraper
from ..STATSport.models.database import get_physical_engine
from ..STATSport.orchestration.orchestration import scrape_by_share_date
from ..SportsDynamics.orchestration.scrape_workflows import (
    initialize_season,
    scrape_round,
    scrape_game,
    scrape_autonomous,
    enrich_players,
)
from ..SportsDynamics.orchestration.task_retention import (
    reconcile_stale_tasks as reconcile_stale_task_records,
)
from ..teams_notifications import send_teams_adaptive_card

logger = logging.getLogger(__name__)

BEAT_CYCLE_STATE_KEY = "scomp:automation:beat-cycle"


def _record_beat_cycle_start() -> datetime:
    """Persist the actual arrival time of the periodic Beat task."""
    started_at = datetime.utcnow()
    redis_client = redis.Redis.from_url(
        os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    redis_client.hset(
        BEAT_CYCLE_STATE_KEY,
        mapping={"started_at": started_at.isoformat()},
    )
    return started_at


def _run_workflow(workflow, task_id: str, *args, **workflow_kwargs):
    """Run an async coordination workflow inside a synchronous Celery worker."""
    import asyncio

    db = SessionLocal()
    try:
        result = asyncio.run(
            workflow(db, *args, task_id=task_id, **workflow_kwargs)
        )
        try:
            task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
            if task and _tactical_match_available(task, result=result, db=db):
                _notify_tactical_task(task, db=db)
        except Exception as notification_error:
            logger.warning("Could not prepare TacticalData notification (%s)", type(notification_error).__name__)
        return result
    except Exception as exc:
        task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)[:4900]
            task.completed_at = datetime.utcnow()
            db.commit()
        try:
            if task and _tactical_match_available(task, db=db):
                _notify_tactical_task(task, workflow_name=workflow.__name__, error=exc, db=db)
        except Exception as notification_error:
            logger.warning("Could not prepare TacticalData failure notification (%s)", type(notification_error).__name__)
        raise
    finally:
        db.close()


def _send_tactical_card(
    status: str,
    status_color: str,
    metrics: list[tuple[str, int]],
    facts: list[tuple[str, str]],
) -> None:
    card = {
        "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "Scomp · TacticalData",
                "weight": "Bolder",
                "size": "Small",
                "color": "Accent",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": status,
                "weight": "Bolder",
                "size": "Large",
                "color": status_color,
                "wrap": True,
            },
            {
                "type": "ColumnSet",
                "spacing": "Medium",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": str(value),
                                "size": "Large",
                                "weight": "Bolder",
                                "horizontalAlignment": "Center",
                                "wrap": True,
                            },
                            {
                                "type": "TextBlock",
                                "text": label,
                                "size": "Small",
                                "isSubtle": True,
                                "horizontalAlignment": "Center",
                                "wrap": True,
                                "spacing": "None",
                            },
                        ],
                    }
                    for label, value in metrics
                ],
            },
            {"type": "FactSet", "facts": [{"title": title, "value": value} for title, value in facts]},
        ],
    }
    send_teams_adaptive_card("tactical", card)


def _utc_time(value: datetime | None) -> str:
    timestamp = value or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)
    return timestamp.strftime("%H:%M UTC")


def _tactical_match_available(task, result: dict | None = None, db=None) -> bool:
    result = result or {}
    workflow = task.workflow
    metadata = task.extra_metadata or {}

    if workflow == "game_scrape":
        if result:
            return bool(result.get("scraped"))
        return bool(
            db
            and db.query(ScrapingLog.id)
            .filter(
                ScrapingLog.task_id == task.id,
                ScrapingLog.context == "game_cleaning",
                ScrapingLog.item_id.isnot(None),
            )
            .first()
        )
    if workflow == "round_scrape":
        scrape_result = result.get("scrape") or {}
        return bool(
            result.get("game_ids")
            or task.total_items
            or task.processed_items
            or scrape_result.get("processed_count")
            or scrape_result.get("error_count")
            or scrape_result.get("skipped_count")
        )
    if workflow == "season_initialization":
        return bool(result.get("games_count") or task.processed_items)
    if workflow == "autonomous_scrape":
        detection = metadata.get("change_detection") or {}
        return bool(
            result.get("detected_count")
            or result.get("processed_game_ids")
            or detection.get("affected_games_count")
        )
    if workflow == "player_enrichment" and db:
        return bool(
            db.query(Game.id)
            .filter(
                Game.competition_id == task.competition_id,
                Game.season_id == task.season_id,
            )
            .first()
        )
    return False


def _notify_tactical_task(
    task,
    workflow_name: str | None = None,
    error: Exception | None = None,
    db=None,
) -> None:
    status = "failed" if error else getattr(task.status, "value", task.status) if task else "failed"
    status_labels = {
        "completed": "Scrape terminé",
        "partial": "Scrape partiel",
        "failed": "Scrape en échec",
        "skipped": "Scrape ignoré",
        "pending": "Scrape en attente",
        "running": "Scrape en cours",
    }
    status_colors = {
        "completed": "Good",
        "partial": "Warning",
        "failed": "Attention",
        "skipped": "Accent",
        "pending": "Default",
        "running": "Default",
    }
    workflow_labels = {
        "game_scrape": "Collecte d’un match",
        "player_enrichment": "Enrichissement des joueurs",
        "round_scrape": "Collecte d’un round",
        "season_initialization": "Initialisation de saison",
    }
    workflow = task.workflow if task else workflow_name or "workflow inconnu"
    workflow_label = workflow_labels.get(workflow, workflow.replace("_", " ").capitalize())
    metrics = [
        ("Traités", int(getattr(task, "processed_items", 0) or 0)),
        ("Total", int(getattr(task, "total_items", 0) or 0)),
        ("Échecs", int(getattr(task, "failed_items", 0) or 0)),
    ]
    if error and metrics[2][1] == 0:
        metrics[2] = ("Échecs", 1)
    facts = [("Heure de fin", _utc_time(getattr(task, "completed_at", None)))]
    if task and task.provider:
        facts.append(("Fournisseur", str(task.provider)))
    facts.append(("Workflow", workflow_label))
    if task and task.round_name:
        facts.append(("Round", str(task.round_name)))
    if task and workflow == "game_scrape" and task.current_item_id:
        game = db.query(Game).filter(Game.id == task.current_item_id).first() if db else None
        if game:
            facts.append(("Match", str(game.name)))
        cleanup_log = (
            db.query(ScrapingLog)
            .filter(
                ScrapingLog.task_id == task.id,
                ScrapingLog.context == "game_cleaning",
                ScrapingLog.item_id == task.current_item_id,
                ScrapingLog.message.contains("Cleaned "),
            )
            .first()
            if db
            else None
        )
        if cleanup_log:
            facts.append(("Type", "Mise à jour"))
    if task and task.id:
        facts.append(("Tâche", str(task.id)))
    if error:
        facts.append(("Erreur", type(error).__name__))
    _send_tactical_card(
        status_labels.get(status, f"Scrape · {status}"),
        status_colors.get(status, "Default"),
        metrics,
        facts,
    )


@app.task(name="scomp.reconcile_stale_tasks")
def reconcile_stale_tasks_task():
    """Mark tasks abandoned by a lost worker without relying on API traffic."""
    db = SessionLocal()
    try:
        reconciled = reconcile_stale_task_records(db)
        return {"status": "completed", "reconciled": reconciled}
    finally:
        db.close()


@app.task(bind=True, name="scomp.initialize_season")
def initialize_season_task(self, task_id: str, competition_id: str, season_id: str):
    return _run_workflow(initialize_season, task_id, competition_id, season_id)


@app.task(bind=True, name="scomp.scrape_round")
def scrape_round_task(
    self,
    task_id: str,
    competition_id: str,
    season_id: str,
    round_name: str,
    parser_names: Optional[List[str]] = None,
):
    return _run_workflow(
        scrape_round,
        task_id,
        competition_id,
        season_id,
        round_name,
        parser_names=parser_names,
    )


@app.task(bind=True, name="scomp.scrape_game")
def scrape_game_task(self, task_id: str, game_id: str):
    return _run_workflow(scrape_game, task_id, game_id)


@app.task(bind=True, name="scomp.scrape_autonomous")
def scrape_autonomous_task(self, task_id: str, competition_id: str, season_id: str):
    return _run_workflow(scrape_autonomous, task_id, competition_id, season_id)


@app.task(bind=True, name="scomp.enrich_players")
def enrich_players_task(self, task_id: str, competition_id: str, season_id: str):
    return _run_workflow(enrich_players, task_id, competition_id, season_id)


@app.task(bind=True, name="scomp.smart_scrape_cycle")
def smart_scrape_cycle(self):
    """
    Execute automated smart scraping cycle
    
    - Detects games matching criteria (time window, status, competition)
    - Scrapes all active competitions
    - Logs activity
    - Runs every SCRAPE_INTERVAL minutes (default 20)
    
    This is the main automated task for production use.
    """
    cycle_started_at = _record_beat_cycle_start()
    logger.info("🤖 Starting smart scrape cycle task at %s", cycle_started_at.isoformat())
    
    try:
        scraper = SmartScraper()
        result = scraper.run()
        
        logger.info(f"✓ Smart scrape cycle completed: {result['status']}")
        logger.info(f"  Competitions: {result['competitions_scraped']}")
        logger.info(f"  Games updated: {result['games_updated']}")

        status = str(result.get("status", "completed")).lower()
        games_updated = int(result.get("games_updated") or 0)
        games_checked = int(result.get("games_checked") or 0)
        if (games_updated or games_checked) and (
            games_updated or status in {"failed", "partial", "error"}
        ):
            failed = int(result.get("failed_items") or result.get("failed") or 0)
            if status in {"failed", "error"} and not failed:
                failed = 1
            status_label = {
                "completed": "Cycle automatique terminé",
                "partial": "Cycle automatique partiel",
                "failed": "Cycle automatique en échec",
                "error": "Cycle automatique en échec",
            }.get(status, f"Cycle automatique · {status}")
            status_color = "Attention" if status in {"failed", "error"} else "Warning" if status == "partial" else "Good"
            _send_tactical_card(
                status_label,
                status_color,
                [
                    ("Compétitions", int(result.get("competitions_scraped") or 0)),
                    ("Matchs actualisés", games_updated),
                    ("Échecs", failed),
                ],
                [("Heure de fin", _utc_time(datetime.now(timezone.utc)))],
            )
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Smart scrape cycle failed: {e}", exc_info=True)
        raise


def _physical_due_configurations() -> list[dict]:
    """Return enabled PhysicalData rules whose weekday, window, and interval are due."""
    now = datetime.now(timezone.utc)
    with get_physical_engine().connect() as connection:
        configurations = connection.execute(text(
            """
            SELECT name, enabled, interval_minutes, window_start_utc, window_end_utc, weekdays
            FROM automation_configurations
            """ )).mappings().all()
        due = []
        for configuration in configurations:
            if not configuration["enabled"] or now.weekday() not in configuration["weekdays"]:
                continue
            current_time = now.time()
            if not configuration["window_start_utc"] <= current_time <= configuration["window_end_utc"]:
                continue
            last_run = connection.execute(text("""
                SELECT started_at FROM scrape_runs
                WHERE scrape_type = 'statsport_automation' AND display_name = :display_name
                ORDER BY started_at DESC LIMIT 1
            """), {"display_name": configuration["name"]}).scalar_one_or_none()
            if not last_run or (now - last_run).total_seconds() >= configuration["interval_minutes"] * 60:
                due.append(dict(configuration))
    return due


def _physical_automation_is_due() -> bool:
    return bool(_physical_due_configurations())


@app.task(bind=True, name="scomp.physical_statsport_automation")
def physical_statsport_automation_task(self):
    """Scrape today's STATSports activities when PhysicalData automation is due."""
    redis_client = redis.Redis.from_url(
        os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    lock = redis_client.lock("scomp:physical:statsport-automation", timeout=30 * 60)
    if not lock.acquire(blocking=False):
        return {"status": "already_running"}
    try:
        if not _physical_automation_is_due():
            return {"status": "not_due"}
        results = []
        now = datetime.now(timezone.utc)
        for configuration in _physical_due_configurations():
            results.append(asyncio.run(scrape_by_share_date(
                now.date(), scrape_type="statsport_automation", display_name=configuration["name"])))
        return {"status": "completed", "rules": results}
    finally:
        lock.release()


@app.task(name="scomp.statsport_automation")
def statsport_automation_task(
    share_date: str | None = None,
    squad_external_id: str | None = None,
    team_name: str | None = None,
):
    """Run a manual STATSports share-date scrape on the dedicated worker."""
    return asyncio.run(
        scrape_by_share_date(
            share_date,
            squad_external_id=squad_external_id,
            team_name=team_name,
        )
    )


@app.task(name="scomp.statsport_date_range")
def statsport_date_range_task(
    start_date: str,
    end_date: str,
    squad_external_id: str | None = None,
    team_name: str | None = None,
):
    """Run a manual STATSports date-range scrape on the dedicated worker."""
    from ..STATSport.orchestration.orchestration import scrape_by_date_range

    return asyncio.run(
        scrape_by_date_range(
            start_date,
            end_date,
            squad_external_id=squad_external_id,
            team_name=team_name,
        )
    )


@app.task(name="scomp.statsport_activity")
def statsport_activity_task(session_date: str, activity_id: str):
    """Run a manual STATSports activity scrape on the dedicated worker."""
    from ..STATSport.orchestration.orchestration import scrape_activity

    return asyncio.run(scrape_activity(session_date, activity_id))


@app.task(name="scomp.statsport_yesterday_share_date")
def statsport_yesterday_share_date_task():
    """Scrape STATSports activities whose ShareDate was yesterday."""
    local_now = datetime.now(ZoneInfo(os.getenv("SCOMP_TIMEZONE", "Europe/Paris")))
    yesterday = (local_now - timedelta(days=1)).date().isoformat()
    return asyncio.run(
        scrape_by_share_date(
            yesterday,
            scrape_type="statsport_yesterday_share_date",
            display_name="Yesterday ShareDate scrape",
        )
    )
