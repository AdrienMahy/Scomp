"""Central task and action tracking for synchronous scrape workflows."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from ..models import ScrapingLog, ScrapingTask, TaskStatus


class TaskTracker:
    """Persist one scrape lifecycle and its detailed actions."""

    def __init__(
        self,
        db: Session,
        provider: str,
        workflow: str,
        competition_id: str,
        season_id: str,
        round_name: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        self.db = db
        self.task = self.db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first() if task_id else None
        if self.task is None:
            self.task = ScrapingTask(
                id=task_id or str(uuid4()),
                provider=provider,
                workflow=workflow,
                competition_id=competition_id,
                season_id=season_id,
                round_name=round_name,
                status=TaskStatus.PENDING,
                extra_metadata=extra_metadata or {},
            )
            self.db.add(self.task)
            self.db.commit()
            self.db.refresh(self.task)

    @property
    def id(self) -> str:
        return self.task.id

    def start(self, total_items: int = 0) -> None:
        self.task.status = TaskStatus.RUNNING
        self.task.started_at = datetime.utcnow()
        self.task.total_items = total_items
        self.task.current_phase = "initialization"
        self._commit()
        self.log("INFO", "Task started", context="task")

    def phase(self, name: str, message: Optional[str] = None) -> None:
        self.task.current_phase = name
        self._commit()
        self.log("INFO", message or f"Phase started: {name}", context=name)

    def progress(
        self,
        processed: Optional[int] = None,
        failed: Optional[int] = None,
        current_item_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        if processed is not None:
            self.task.processed_items = processed
        if failed is not None:
            self.task.failed_items = failed
        if current_item_id is not None:
            self.task.current_item_id = current_item_id
        self._commit()
        if message:
            self.log("INFO", message, context=self.task.current_phase, item_id=current_item_id)

    def cancellation_requested(self) -> bool:
        """Read the cancellation flag written by the API process."""
        self.db.expire(self.task, ["cancel_requested"])
        return bool(self.task.cancel_requested)

    def log(
        self,
        level: str,
        message: str,
        context: Optional[str] = None,
        round_name: Optional[str] = None,
        item_id: Optional[str] = None,
        item_name: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> ScrapingLog:
        entry = ScrapingLog(
            id=str(uuid4()),
            task_id=self.id,
            level=level.upper(),
            message=message,
            context=context or self.task.current_phase,
            round=round_name or self.task.round_name,
            item_id=item_id,
            item_name=item_name,
            stats=stats,
            timestamp=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def item_error(
        self,
        message: str,
        item_id: str,
        item_name: Optional[str] = None,
        round_name: Optional[str] = None,
        context: Optional[str] = None,
    ) -> None:
        self.task.failed_items = (self.task.failed_items or 0) + 1
        self._commit()
        self.log(
            "ERROR",
            message,
            context=context or self.task.current_phase,
            round_name=round_name,
            item_id=item_id,
            item_name=item_name,
        )

    def finish(self, status: str = "completed", message: Optional[str] = None) -> None:
        self.task.status = TaskStatus(status)
        self.task.completed_at = datetime.utcnow()
        self.task.current_phase = "cancelled" if status == "cancelled" else "completed" if status in {"completed", "partial"} else "failed"
        if message:
            self.task.error_message = message if status in {"failed", "partial"} else None
        self._commit()
        self.log(
            "ERROR" if status == "failed" else "WARNING" if status in {"partial", "cancelled"} else "INFO",
            message or f"Task finished with status: {status}",
            context="task",
        )

    def cancel(self, message: str = "Task cancelled manually") -> None:
        self.finish("cancelled", message)

    def fail(self, message: str) -> None:
        self.task.error_message = message[:4900]
        self.finish("failed", message)

    def _commit(self) -> None:
        self.db.add(self.task)
        self.db.commit()
        self.db.refresh(self.task)
