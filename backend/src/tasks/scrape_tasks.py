"""Celery scraping tasks"""
from datetime import datetime, timezone
import asyncio
import logging
import os

import redis
from sqlalchemy import text

from .celery_config import app
from ..config.database import SessionLocal
from ..SportsDynamics.models import ScrapingTask, TaskStatus
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


def _run_workflow(workflow, task_id: str, *args):
    """Run an async coordination workflow inside a synchronous Celery worker."""
    import asyncio

    db = SessionLocal()
    try:
        return asyncio.run(workflow(db, *args, task_id=task_id))
    except Exception as exc:
        task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)[:4900]
            task.completed_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()


@app.task(bind=True, name="scomp.initialize_season")
def initialize_season_task(self, task_id: str, competition_id: str, season_id: str):
    return _run_workflow(initialize_season, task_id, competition_id, season_id)


@app.task(bind=True, name="scomp.scrape_round")
def scrape_round_task(self, task_id: str, competition_id: str, season_id: str, round_name: str):
    return _run_workflow(scrape_round, task_id, competition_id, season_id, round_name)


@app.task(bind=True, name="scomp.scrape_game")
def scrape_game_task(self, task_id: str, game_id: str):
    return _run_workflow(scrape_game, task_id, game_id)


@app.task(bind=True, name="scomp.scrape_autonomous")
def scrape_autonomous_task(self, task_id: str, competition_id: str, season_id: str):
    return _run_workflow(scrape_autonomous, task_id, competition_id, season_id)


@app.task(bind=True, name="scomp.enrich_players")
def enrich_players_task(self, task_id: str, competition_id: str, season_id: str):
    return _run_workflow(enrich_players, task_id, competition_id, season_id)


@app.task(bind=True)
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
