"""Authenticated run metrics for the PhysicalData and TacticalData pipelines."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, case, cast, func, text, true
from sqlalchemy.orm import Session

from src.STATSport.models.database import get_physical_engine
from src.SportsDynamics.models import ScrapingLog, ScrapingTask
from src.auth import User, current_user, get_db


router = APIRouter(prefix="/metrics", tags=["pipeline metrics"])


def _as_int(value: Any) -> int:
    return int(value or 0)


def _duration_seconds(started_at: datetime | None, completed_at: datetime | None) -> float | None:
    if not started_at:
        return None
    end = completed_at or datetime.utcnow()
    if started_at.tzinfo and not end.tzinfo:
        end = end.replace(tzinfo=started_at.tzinfo)
    elif end.tzinfo and not started_at.tzinfo:
        started_at = started_at.replace(tzinfo=end.tzinfo)
    return round(max(0.0, (end - started_at).total_seconds()), 1)


def _physical_metrics(cutoff: datetime, limit: int = 12) -> dict[str, Any]:
    with get_physical_engine().connect() as connection:
        summary = connection.execute(text("""
            SELECT COUNT(*) AS runs,
                   COUNT(*) FILTER (WHERE completed_at IS NOT NULL) AS finished_runs,
                   COUNT(*) FILTER (WHERE lower(status) IN ('completed', 'success')) AS completed_runs,
                   COUNT(*) FILTER (WHERE lower(status) IN ('failed', 'error', 'partial')) AS error_runs,
                   COALESCE(SUM(inserted), 0) AS inserted_items,
                   COALESCE(SUM(updated), 0) AS updated_items,
                   COALESCE(SUM(skipped), 0) AS skipped_items,
                   COALESCE(SUM(failed), 0) AS failed_items,
                   COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
                       FILTER (WHERE completed_at IS NOT NULL AND started_at IS NOT NULL), 0)
                       AS average_duration_seconds
            FROM scrape_runs
            WHERE started_at >= :cutoff
        """), {"cutoff": cutoff}).mappings().one()

        daily = connection.execute(text("""
            SELECT date_trunc('day', started_at)::date AS date,
                   COUNT(*) AS runs,
                   COUNT(*) FILTER (WHERE lower(status) IN ('failed', 'error', 'partial')) AS error_runs,
                     COALESCE(SUM(inserted), 0) AS inserted_items,
                     COALESCE(SUM(updated), 0) AS updated_items,
                   COALESCE(SUM(failed), 0) AS failed_items,
                   COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
                       FILTER (WHERE completed_at IS NOT NULL AND started_at IS NOT NULL), 0)
                       AS average_duration_seconds
            FROM scrape_runs
            WHERE started_at >= :cutoff
            GROUP BY date_trunc('day', started_at)::date
            ORDER BY date
        """), {"cutoff": cutoff}).mappings()

        recent = connection.execute(text("""
                 SELECT id::text AS id, COALESCE(display_name, scrape_type) AS name,
                     scrape_type, lower(status) AS status, found,
                     inserted AS inserted_items, updated AS updated_items,
                     skipped AS skipped_items, failed AS failed_items, started_at, completed_at,
                   CASE WHEN started_at IS NULL THEN NULL
                        ELSE GREATEST(0, EXTRACT(EPOCH FROM (COALESCE(completed_at, now()) - started_at)))
                   END AS duration_seconds
            FROM scrape_runs
            WHERE started_at >= :cutoff
            ORDER BY started_at DESC
            LIMIT :limit
        """), {"cutoff": cutoff, "limit": limit}).mappings()

    return {
        "metrics": {
            key: float(value) if key == "average_duration_seconds" else _as_int(value)
            for key, value in summary.items()
        },
        "daily": [dict(row) for row in daily],
        "recent_runs": [dict(row) for row in recent],
    }


def _tactical_metrics(db: Session, cutoff: datetime, limit: int = 12) -> dict[str, Any]:
    table_stats = func.json_each(ScrapingLog.stats).table_valued("key", "value").lateral("table_stats")
    inserted_value = cast(table_stats.c.value.op("->>")("inserted"), Integer)
    deleted_value = cast(table_stats.c.value.op("->>")("deleted"), Integer)
    per_task_stats = (
        db.query(
            ScrapingLog.task_id.label("task_id"),
            func.coalesce(func.sum(inserted_value), 0).label("inserted_rows"),
            func.coalesce(func.sum(deleted_value), 0).label("deleted_rows"),
        )
        .select_from(ScrapingLog)
        .join(ScrapingTask, ScrapingLog.task_id == ScrapingTask.id)
        .join(table_stats, true())
        .filter(ScrapingTask.created_at >= cutoff)
        .group_by(ScrapingLog.task_id)
        .subquery()
    )
    inserted_rows = func.coalesce(per_task_stats.c.inserted_rows, 0)
    deleted_rows = func.coalesce(per_task_stats.c.deleted_rows, 0)
    run_duration = func.extract("epoch", ScrapingTask.completed_at - ScrapingTask.started_at)
    failed_status = ScrapingTask.status.in_(["failed", "partial"])

    summary = db.query(
        func.count(ScrapingTask.id).label("runs"),
        func.sum(case((ScrapingTask.completed_at.is_not(None), 1), else_=0)).label("finished_runs"),
        func.sum(case((ScrapingTask.status == "completed", 1), else_=0)).label("completed_runs"),
        func.sum(case((failed_status, 1), else_=0)).label("error_runs"),
        func.coalesce(func.sum(ScrapingTask.processed_items), 0).label("processed_items"),
        func.coalesce(func.sum(ScrapingTask.failed_items), 0).label("failed_items"),
        func.coalesce(func.sum(inserted_rows), 0).label("inserted_rows"),
        func.coalesce(func.sum(deleted_rows), 0).label("deleted_rows"),
        func.coalesce(
            func.avg(run_duration).filter(
                ScrapingTask.started_at.is_not(None), ScrapingTask.completed_at.is_not(None)
            ),
            0,
        ).label("average_duration_seconds"),
    ).outerjoin(per_task_stats, per_task_stats.c.task_id == ScrapingTask.id).filter(
        ScrapingTask.created_at >= cutoff
    ).one()

    daily_rows = db.query(
        func.date(ScrapingTask.created_at).label("date"),
        func.count(ScrapingTask.id).label("runs"),
        func.sum(case((failed_status, 1), else_=0)).label("error_runs"),
        func.coalesce(func.sum(ScrapingTask.processed_items), 0).label("processed_items"),
        func.coalesce(func.sum(ScrapingTask.failed_items), 0).label("failed_items"),
        func.coalesce(func.sum(inserted_rows), 0).label("inserted_rows"),
        func.coalesce(func.sum(deleted_rows), 0).label("deleted_rows"),
        func.coalesce(
            func.avg(run_duration).filter(
                ScrapingTask.started_at.is_not(None), ScrapingTask.completed_at.is_not(None)
            ),
            0,
        ).label("average_duration_seconds"),
    ).outerjoin(per_task_stats, per_task_stats.c.task_id == ScrapingTask.id).filter(
        ScrapingTask.created_at >= cutoff
    ).group_by(func.date(ScrapingTask.created_at)).order_by(func.date(ScrapingTask.created_at)).all()

    recent_rows = db.query(
        ScrapingTask,
        inserted_rows.label("inserted_rows"),
        deleted_rows.label("deleted_rows"),
    ).outerjoin(per_task_stats, per_task_stats.c.task_id == ScrapingTask.id).filter(
        ScrapingTask.created_at >= cutoff
    ).order_by(ScrapingTask.created_at.desc()).limit(limit).all()

    metrics = {
        key: float(value or 0) if key == "average_duration_seconds" else _as_int(value)
        for key, value in summary._mapping.items()
    }
    daily = [
        {
            key: (value.isoformat() if key == "date" and value else
                  float(value or 0) if key == "average_duration_seconds" else
                  _as_int(value) if key != "date" else None)
            for key, value in row._mapping.items()
        }
        for row in daily_rows
    ]
    recent_runs = []
    for task, inserted, deleted in recent_rows:
        recent_runs.append({
            "id": task.id,
            "name": task.workflow,
            "provider": task.provider,
            "status": task.status,
            "total_items": _as_int(task.total_items),
            "processed_items": _as_int(task.processed_items),
            "failed_items": _as_int(task.failed_items),
            "inserted_rows": _as_int(inserted),
            "updated_rows": None,
            "deleted_rows": _as_int(deleted),
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "duration_seconds": _duration_seconds(task.started_at, task.completed_at),
        })

    return {"metrics": metrics, "daily": daily, "recent_runs": recent_runs}


@router.get("/pipelines")
def get_pipeline_metrics(
    days: int = Query(default=30, ge=7, le=90),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return pipeline metrics to administrators only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Accès administrateur requis")

    cutoff = datetime.utcnow() - timedelta(days=days)
    entities: dict[str, Any] = {}
    entities["physical"] = _physical_metrics(cutoff)
    entities["tactical"] = _tactical_metrics(db, cutoff)
    return {"range_days": days, "entities": entities}