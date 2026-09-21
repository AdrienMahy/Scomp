"""Celery scraping tasks"""
from datetime import datetime
import logging
import os

import redis

from .celery_config import app
from ..config.database import SessionLocal
from ..models import ScrapingTask, TaskStatus
from ..automation import SmartScraper
from ..orchestration.scrape_workflows import (
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
