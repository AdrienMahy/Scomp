"""Celery Beat scheduling configuration"""
from celery.schedules import schedule
from .celery_config import app
from ..SportsDynamics.automation.scheduler_config import AutomationConfig

# Get scrape interval from config or environment
SCRAPE_INTERVAL = AutomationConfig.SCRAPE_INTERVAL
AUTOMATION_ENABLED = AutomationConfig.AUTOMATION_ENABLED

print(
    f"🔔 Celery Beat automation {'enabled' if AUTOMATION_ENABLED else 'disabled'}"
    f" - scrape interval: {SCRAPE_INTERVAL} minutes"
)

# Register the autonomous workflow only when explicitly enabled. Manual scrape
# tasks remain available regardless of this setting.
app.conf.beat_schedule = {
    'smart-scrape-cycle': {
        'task': 'src.tasks.scrape_tasks.smart_scrape_cycle',
        'schedule': schedule(run_every=SCRAPE_INTERVAL * 60),
        'options': {
            'expires': (SCRAPE_INTERVAL + 5) * 60,
        },
        'kwargs': {},
    },
} if AUTOMATION_ENABLED else {}

app.conf.beat_schedule["physical-statsport-automation"] = {
    "task": "scomp.physical_statsport_automation",
    "schedule": schedule(run_every=300),
    "options": {"expires": 295},
    "kwargs": {},
}

# Enable UTC timezone
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

