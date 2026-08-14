"""Scraping tasks routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from ...config.database import get_db
from ...models import ScrapingTask, TaskStatus
from ...web.schemas import ScrapingTaskRead, ScrapingTaskCreate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[ScrapingTaskRead])
def list_tasks(db: Session = Depends(get_db)):
    """List all scraping tasks"""
    tasks = db.query(ScrapingTask).all()
    return tasks


@router.get("/{task_id}", response_model=ScrapingTaskRead)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get task by ID"""
    task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=ScrapingTaskRead)
def create_task(task_data: ScrapingTaskCreate, db: Session = Depends(get_db)):
    """Create a new scraping task"""
    task = ScrapingTask(
        id=str(uuid.uuid4()),
        provider=task_data.provider,
        competition_id=task_data.competition_id,
        season_id=task_data.season_id,
        status=TaskStatus.PENDING,
        metadata=task_data.metadata
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
