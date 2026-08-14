"""Celery Beat scheduling"""
from celery.schedules import crontab
from .celery_config import app

# Schedule periodic tasks here
app.conf.beat_schedule = {
    # Example: scrape every day at 2 AM UTC
    # "scrape-daily": {
    #     "task": "src.tasks.scrape_tasks.scrape_sportsdynamics_competition",
    #     "schedule": crontab(hour=2, minute=0),
    # },
}
