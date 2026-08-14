"""Celery scraping tasks"""
from datetime import datetime
import logging

from .celery_config import app
from ..config.database import SessionLocal
from ..models import ScrapingTask, TaskStatus
from ..scraper import SportsDynamicsScraper

logger = logging.getLogger(__name__)


@app.task(bind=True)
def scrape_sportsdynamics_competition(self, task_id: str, competition_id: str, season_id: str):
    """
    Scrape SportsDynamics competition
    
    Args:
        task_id: Task ID for progress tracking
        competition_id: Competition to scrape
        season_id: Season to scrape
    """
    db = SessionLocal()
    
    try:
        # Get task
        task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        # Update status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        db.commit()
        
        # Run scraper
        scraper = SportsDynamicsScraper()
        result = scraper.scrape_competition(competition_id, season_id, db)
        
        # Update task
        task.total_items = result.get("games", 0)
        task.processed_items = result.get("games", 0)
        task.failed_items = len(result.get("errors", []))
        task.status = TaskStatus.COMPLETED if not result.get("errors") else TaskStatus.FAILED
        task.completed_at = datetime.utcnow()
        
        if result.get("errors"):
            task.error_message = "; ".join(result["errors"])
        
        db.commit()
        logger.info(f"Task {task_id} completed: {result}")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        
    finally:
        db.close()
