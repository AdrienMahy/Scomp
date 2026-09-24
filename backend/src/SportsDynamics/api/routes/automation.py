"""Automation routes for smart scraping management"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import os
import redis

from src.config.database import get_db
from src.SportsDynamics.models import ScrapingTask, Competition, Game, AutomationConfiguration
from src.SportsDynamics.automation.scheduler_config import AutomationConfig
from src.SportsDynamics.automation.monitor import ScrapingMonitor
from src.SportsDynamics.automation.smart_scraper import SmartScraper
from src.SportsDynamics.orchestration.task_retention import reconcile_stale_tasks
from src.tasks.scrape_tasks import BEAT_CYCLE_STATE_KEY

router = APIRouter(prefix="/sportsdynamics/automation", tags=["sportsdynamics-automation"])


# Schemas
class AutomationStatus:
    """Status of automation system"""
    is_enabled: bool
    scrape_interval_minutes: int
    active_competitions: int
    last_scrape_at: Optional[datetime]
    next_scrape_at: Optional[datetime]
    total_games_checked: int
    total_games_updated: int

    def __init__(self, data: dict):
        self.__dict__.update(data)


# Pydantic schemas for configuration management
class AutomationConfigCreateSchema(BaseModel):
    """Schema for creating new automation configuration"""
    name: str
    description: Optional[str] = None
    competition_id: str
    competition_name: str
    season_id: str
    season_name: Optional[str] = None
    provider: str = "sportsdynamics"
    scrape_interval_minutes: int = 20
    enabled: bool = True
    look_ahead_days: int = 7
    look_back_days: int = 1
    live_game_window_minutes: int = 120
    task_timeout_seconds: int = 30 * 60


class AutomationConfigUpdateSchema(BaseModel):
    """Schema for updating automation configuration"""
    name: Optional[str] = None
    description: Optional[str] = None
    competition_id: Optional[str] = None
    competition_name: Optional[str] = None
    season_name: Optional[str] = None
    scrape_interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None
    look_ahead_days: Optional[int] = None
    look_back_days: Optional[int] = None
    live_game_window_minutes: Optional[int] = None
    task_timeout_seconds: Optional[int] = None


class AutomationConfigResponseSchema(BaseModel):
    """Schema for automation configuration response"""
    id: str
    name: str
    description: Optional[str]
    competition_id: str
    competition_name: str
    season_id: str
    season_name: Optional[str]
    provider: str
    scrape_interval_minutes: int
    enabled: bool
    look_ahead_days: int
    look_back_days: int
    live_game_window_minutes: int
    task_timeout_seconds: int
    created_at: Optional[str]
    updated_at: Optional[str]
    last_execution_at: Optional[str] = None
    next_refresh_at: Optional[str] = None
    execution_status: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/status")
def get_automation_status(db: Session = Depends(get_db)):
    """Get current automation status"""
    try:
        reconcile_stale_tasks(db)
        monitor = ScrapingMonitor()
        active_comps = AutomationConfig.get_active_competitions()
        
        # Get last scrape
        last_scrape = db.query(ScrapingTask).filter(
            ScrapingTask.workflow == "autonomous_scrape"
        ).order_by(ScrapingTask.created_at.desc()).first()
        
        # Calculate next scrape (roughly)
        next_scrape = None
        if AutomationConfig.AUTOMATION_ENABLED and last_scrape:
            next_scrape = last_scrape.created_at + timedelta(minutes=AutomationConfig.SCRAPE_INTERVAL)
        
        # Get total games stats
        total_games = db.query(Game).count()
        
        # Get look_ahead/back from first active competition
        look_ahead = active_comps[0]["look_ahead_days"] if active_comps else 7
        look_back = active_comps[0]["look_back_days"] if active_comps else 1
        
        return {
            "status": "active" if AutomationConfig.AUTOMATION_ENABLED else "disabled",
            "is_enabled": AutomationConfig.AUTOMATION_ENABLED and len(active_comps) > 0,
            "scrape_interval_minutes": AutomationConfig.SCRAPE_INTERVAL,
            "active_competitions": len(active_comps),
            "active_competition_names": [c["name"] for c in active_comps],
            "last_scrape_at": last_scrape.created_at if last_scrape else None,
            "next_scrape_at": next_scrape,
            "total_games_in_db": total_games,
            "look_ahead_days": look_ahead,
            "look_back_days": look_back,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


def _configuration_with_schedule(config: AutomationConfiguration, db: Session) -> dict:
    """Add execution status and the next tick from the global Beat cycle."""
    result = config.to_dict()
    beat_state = redis.Redis.from_url(
        os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    ).hgetall(BEAT_CYCLE_STATE_KEY)
    beat_started_at = beat_state.get("started_at")
    if AutomationConfig.AUTOMATION_ENABLED and beat_started_at:
        beat_started = datetime.fromisoformat(beat_started_at)
        result["last_execution_at"] = beat_started.isoformat()
        result["next_refresh_at"] = (
            beat_started + timedelta(minutes=AutomationConfig.SCRAPE_INTERVAL)
        ).isoformat()
    else:
        result["last_execution_at"] = None
        result["next_refresh_at"] = None

    last_task = db.query(ScrapingTask).filter(
        ScrapingTask.workflow == "autonomous_scrape",
        ScrapingTask.competition_id == config.competition_id,
        ScrapingTask.season_id == config.season_id,
    ).order_by(ScrapingTask.created_at.desc()).first()
    if last_task:
        result["execution_status"] = last_task.status.value if hasattr(last_task.status, "value") else last_task.status
    else:
        result["execution_status"] = None
    return result


@router.get("/config")
def get_automation_config():
    """Get current automation configuration"""
    try:
        active_comps = AutomationConfig.get_active_competitions()
        # Get look_ahead/back from first active competition
        look_ahead = active_comps[0]["look_ahead_days"] if active_comps else 7
        look_back = active_comps[0]["look_back_days"] if active_comps else 1
        
        return {
            "scrape_interval_minutes": AutomationConfig.SCRAPE_INTERVAL,
            "look_ahead_days": look_ahead,
            "look_back_days": look_back,
            "live_game_window_minutes": AutomationConfig.LIVE_GAME_WINDOW,
            "max_concurrent_scrapes": AutomationConfig.MAX_CONCURRENT_SCRAPES,
            "task_timeout_seconds": AutomationConfig.TASK_TIMEOUT,
            "active_competitions": active_comps,
            "competitions_count": len(active_comps),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting config: {str(e)}")


@router.get("/logs")
def get_automation_logs(
    limit: int = 50,
    hours: int = 24,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get automation logs from the database
    
    Args:
        limit: Maximum number of logs to return (default: 50)
        hours: Look back period in hours (default: 24)
        status: Filter by status (success, error, pending)
    """
    try:
        reconcile_stale_tasks(db)
        query = db.query(ScrapingTask).filter(ScrapingTask.workflow == "autonomous_scrape")
        
        # Filter by time
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(ScrapingTask.created_at >= cutoff_time)
        
        # Filter by status
        if status:
            query = query.filter(ScrapingTask.status == status)
        
        # Order by most recent first
        logs = query.order_by(ScrapingTask.created_at.desc()).limit(limit).all()
        competition_names = {
            competition.id: competition.name
            for competition in db.query(Competition).all()
        }
        
        return {
            "logs": [
                {
                    "id": log.id,
                    "competition_id": log.competition_id,
                    "competition_name": competition_names.get(log.competition_id, log.competition_id),
                    "status": log.status,
                    "games_count": log.processed_items,
                    "error_message": log.error_message,
                    "change_detection": (log.extra_metadata or {}).get("change_detection", {}),
                    "executed_at": log.created_at,
                }
                for log in logs
            ],
            "total": len(logs),
            "hours": hours,
            "status_filter": status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting logs: {str(e)}")


@router.get("/statistics")
def get_automation_statistics(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get automation statistics for the specified period"""
    try:
        monitor = ScrapingMonitor()
        stats = monitor.get_statistics(hours)
        
        # Also get per-competition breakdown
        query = db.query(ScrapingTask.competition_id, ScrapingTask.status).filter(
            ScrapingTask.workflow == "autonomous_scrape"
        )
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(ScrapingTask.created_at >= cutoff_time)
        
        logs = query.all()
        comp_stats = {}
        for log in logs:
            comp_id = log.competition_id
            if comp_id not in comp_stats:
                comp_stats[comp_id] = {"success": 0, "error": 0}
            if log.status == "success":
                comp_stats[comp_id]["success"] += 1
            else:
                comp_stats[comp_id]["error"] += 1
        
        return {
            "period_hours": hours,
            "total_scrapes": stats.get("total_scrapes", 0),
            "successful": stats.get("successful", 0),
            "failed": stats.get("failed", 0),
            "success_rate_percent": stats.get("success_rate", 0),
            "total_games_processed": stats.get("total_games_processed", 0),
            "avg_games_per_scrape": stats.get("avg_games_per_scrape", 0),
            "per_competition": comp_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")


# Legacy route retained as an internal implementation; not exposed publicly.
def run_scrape_cycle_immediate(db: Session = Depends(get_db)):
    """Trigger a scraping cycle immediately (synchronous)"""
    try:
        scraper = SmartScraper()
        result = scraper.run()
        return {
            "status": "completed",
            "message": "Scraping cycle executed",
            "result": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error running scrape cycle: {str(e)}",
            "error": str(e),
        }


@router.get("/last-scrape")
def get_last_scrape(db: Session = Depends(get_db)):
    """Get details about the last scraping execution"""
    try:
        reconcile_stale_tasks(db)
        last_log = db.query(ScrapingTask).filter(
            ScrapingTask.workflow == "autonomous_scrape"
        ).order_by(ScrapingTask.created_at.desc()).first()
        
        if not last_log:
            return {
                "executed_at": None,
                "status": "no_execution",
                "message": "No scraping has been executed yet",
            }
        
        return {
            "executed_at": last_log.created_at,
            "status": last_log.status,
            "competition_id": last_log.competition_id,
            "games_count": last_log.processed_items,
            "error_message": last_log.error_message,
            "time_since_last_scrape": (datetime.utcnow() - last_log.created_at).total_seconds(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting last scrape: {str(e)}")


@router.get("/health")
def automation_health_check():
    """Check if automation system is healthy"""
    try:
        # Try to instantiate SmartScraper to verify imports
        scraper = SmartScraper()
        config = AutomationConfig()
        
        return {
            "status": "healthy",
            "automation_enabled": len(AutomationConfig.get_active_competitions()) > 0,
            "timestamp": datetime.utcnow(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow(),
        }


# ============================================================================
# Configuration Management Routes
# ============================================================================

@router.get("/configurations", response_model=List[AutomationConfigResponseSchema])
def list_automation_configurations(
    enabled_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all automation configurations"""
    try:
        reconcile_stale_tasks(db)
        query = db.query(AutomationConfiguration)
        if enabled_only:
            query = query.filter(AutomationConfiguration.enabled == True)
        configs = query.order_by(AutomationConfiguration.created_at.desc()).all()
        return [_configuration_with_schedule(config, db) for config in configs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing configurations: {str(e)}")


@router.get("/configurations/{config_id}", response_model=AutomationConfigResponseSchema)
def get_automation_configuration(
    config_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific automation configuration"""
    try:
        config = db.query(AutomationConfiguration).filter(
            AutomationConfiguration.id == config_id
        ).first()
        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        return config.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting configuration: {str(e)}")


@router.post("/configurations", response_model=AutomationConfigResponseSchema)
def create_automation_configuration(
    payload: AutomationConfigCreateSchema,
    db: Session = Depends(get_db)
):
    """Create a new automation configuration"""
    try:
        competition = db.query(Competition).filter(Competition.id == payload.competition_id).first()
        if not competition:
            raise HTTPException(status_code=400, detail=f"Competition {payload.competition_id} not found")

        config = AutomationConfiguration(
            name=payload.name,
            description=payload.description,
            competition_id=payload.competition_id,
            competition_name=payload.competition_name,
            season_id=payload.season_id,
            season_name=payload.season_name,
            provider=payload.provider,
            scrape_interval_minutes=payload.scrape_interval_minutes,
            enabled=payload.enabled,
            look_ahead_days=payload.look_ahead_days,
            look_back_days=payload.look_back_days,
            live_game_window_minutes=payload.live_game_window_minutes,
            task_timeout_seconds=payload.task_timeout_seconds,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        return config.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating configuration: {str(e)}")


@router.put("/configurations/{config_id}", response_model=AutomationConfigResponseSchema)
def update_automation_configuration(
    config_id: str,
    payload: AutomationConfigUpdateSchema,
    db: Session = Depends(get_db)
):
    """Update an automation configuration"""
    try:
        config = db.query(AutomationConfiguration).filter(
            AutomationConfiguration.id == config_id
        ).first()
        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Update only provided fields
        update_data = payload.dict(exclude_unset=True)
        if "competition_id" in update_data:
            competition = db.query(Competition).filter(
                Competition.id == update_data["competition_id"]
            ).first()
            if not competition:
                raise HTTPException(
                    status_code=400,
                    detail=f"Competition {update_data['competition_id']} not found",
                )
        for key, value in update_data.items():
            setattr(config, key, value)
        
        db.commit()
        db.refresh(config)
        return config.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating configuration: {str(e)}")


@router.delete("/configurations/{config_id}")
def delete_automation_configuration(
    config_id: str,
    db: Session = Depends(get_db)
):
    """Delete an automation configuration"""
    try:
        config = db.query(AutomationConfiguration).filter(
            AutomationConfiguration.id == config_id
        ).first()
        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        db.delete(config)
        db.commit()
        return {"message": f"Configuration {config_id} deleted", "id": config_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting configuration: {str(e)}")
