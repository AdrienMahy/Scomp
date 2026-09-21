"""Celery Beat scheduling configuration"""
from celery.schedules import schedule
from .celery_config import app
from ..automation.scheduler_config import AutomationConfig
import os

# Get scrape interval from config or environment
SCRAPE_INTERVAL = AutomationConfig.SCRAPE_INTERVAL

print(f"🔔 Celery Beat configured - Scrape interval: {SCRAPE_INTERVAL} minutes")

# Schedule the autonomous workflow. It remains inert until a competition is
# explicitly enabled in AutomationConfig.
app.conf.beat_schedule = {
    'smart-scrape-cycle': {
        'task': 'src.tasks.scrape_tasks.smart_scrape_cycle',
        'schedule': schedule(run_every=SCRAPE_INTERVAL * 60),
        'options': {
            'expires': (SCRAPE_INTERVAL + 5) * 60,
        },
        'kwargs': {},
    },
}

# Enable UTC timezone
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

