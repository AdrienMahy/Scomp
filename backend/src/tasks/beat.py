"""Celery Beat scheduling configuration"""
from celery.schedules import crontab, schedule
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
        'task': 'scomp.smart_scrape_cycle',
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

app.conf.beat_schedule["reconcile-stale-tasks"] = {
    "task": "scomp.reconcile_stale_tasks",
    "schedule": schedule(run_every=60),
    "options": {"expires": 55},
    "kwargs": {},
}

# Use the local project timezone for clock-based schedules.
app.conf.timezone = app.conf.timezone or 'Europe/Paris'
app.conf.enable_utc = True

app.conf.beat_schedule["statsport-yesterday-share-date"] = {
    "task": "scomp.statsport_yesterday_share_date",
    "schedule": crontab(minute=30, hour=8),
    "options": {"expires": 60 * 60},
    "kwargs": {},
}
