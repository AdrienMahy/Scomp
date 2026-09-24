"""Retention policy for scrape task history."""
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from ..models import ScrapingLog, ScrapingTask, TaskStatus

TASK_HISTORY_DAYS = 30
TASK_TIMEOUT_SECONDS = 30 * 60


def reconcile_stale_tasks(db: Session, timeout_seconds: int = TASK_TIMEOUT_SECONDS) -> int:
    """Mark running tasks abandoned after their worker timeout as failed."""
    cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)
    stale_tasks = db.query(ScrapingTask).filter(
        ScrapingTask.status == TaskStatus.RUNNING,
        ScrapingTask.started_at.isnot(None),
        ScrapingTask.started_at < cutoff,
    ).all()

    for task in stale_tasks:
        message = f"Task stopped responding after {timeout_seconds // 60} minutes; worker execution is no longer active."
        task.status = TaskStatus.FAILED
        task.error_message = message
        task.completed_at = datetime.utcnow()
        task.current_phase = "failed"
        db.add(ScrapingLog(
            id=str(uuid4()),
            task_id=task.id,
            level="ERROR",
            message=message,
            context="task_recovery",
            timestamp=datetime.utcnow(),
        ))

    if stale_tasks:
        db.commit()
    return len(stale_tasks)


def purge_task_history(db: Session, retention_days: int = TASK_HISTORY_DAYS) -> dict:
    """Delete task history older than the configured retention period."""
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    old_task_ids = [
        task_id
        for (task_id,) in db.query(ScrapingTask.id)
        .filter(ScrapingTask.created_at < cutoff)
        .all()
    ]
    deleted_logs = 0
    deleted_tasks = 0
    if old_task_ids:
        deleted_logs = (
            db.query(ScrapingLog)
            .filter(ScrapingLog.task_id.in_(old_task_ids))
            .delete(synchronize_session=False)
        )
        deleted_tasks = (
            db.query(ScrapingTask)
            .filter(ScrapingTask.id.in_(old_task_ids))
            .delete(synchronize_session=False)
        )
    db.commit()
    return {
        "cutoff": cutoff,
        "deleted_logs": deleted_logs,
        "deleted_tasks": deleted_tasks,
    }
