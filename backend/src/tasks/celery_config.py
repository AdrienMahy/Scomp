"""Celery configuration"""
from celery import Celery
import os

# Create Celery app
app = Celery(
    "scomp",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

app.conf.task_routes = {
    "scomp.initialize_season": {"queue": "sportsdynamics"},
    "scomp.scrape_round": {"queue": "sportsdynamics"},
    "scomp.scrape_game": {"queue": "sportsdynamics"},
    "scomp.scrape_autonomous": {"queue": "sportsdynamics"},
    "scomp.enrich_players": {"queue": "sportsdynamics"},
    "scomp.smart_scrape_cycle": {"queue": "sportsdynamics"},
    "scomp.reconcile_stale_tasks": {"queue": "sportsdynamics"},
    "scomp.physical_statsport_automation": {"queue": "statsport"},
    "scomp.statsport_automation": {"queue": "statsport"},
    "scomp.statsport_date_range": {"queue": "statsport"},
    "scomp.statsport_activity": {"queue": "statsport"},
}
