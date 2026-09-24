"""Scheduler configuration for automated scraping"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os


class AutomationConfig:
    """Configuration for automated scraping schedules"""

    AUTOMATION_ENABLED = os.getenv("AUTOMATION_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    
    # Scraping schedule (in minutes)
    SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "20"))  # Default: 20 minutes
    
    # Deprecated: Use AutomationConfiguration model from database
    # Keep for backward compatibility
    COMPETITIONS_TO_SCRAPE: List[Dict[str, Any]] = []
    
    # Time window for "live" games (minutes)
    LIVE_GAME_WINDOW = 120  # Consider a game "live" if started within last 120 min
    
    # Max concurrent scraping tasks
    MAX_CONCURRENT_SCRAPES = 2
    
    # Task timeout (seconds)
    TASK_TIMEOUT = 30 * 60  # 30 minutes
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_SCRAPE_LOGGING = True
    
    @staticmethod
    def get_active_competitions() -> List[Dict[str, Any]]:
        """Get list of active competitions to scrape from database"""
        try:
            # Import here to avoid circular imports
            from src.config.database import SessionLocal
            from ..models import AutomationConfiguration
            
            db = SessionLocal()
            try:
                configs = db.query(AutomationConfiguration).filter(
                    AutomationConfiguration.enabled == True
                ).all()
                
                return [
                    {
                        "id": c.competition_id,
                        "name": c.competition_name,
                        "season_id": c.season_id,
                        "provider": c.provider,
                        "look_ahead_days": c.look_ahead_days,
                        "look_back_days": c.look_back_days,
                        "scrape_interval_minutes": c.scrape_interval_minutes,
                        "live_game_window_minutes": c.live_game_window_minutes,
                        "task_timeout_seconds": c.task_timeout_seconds,
                    }
                    for c in configs
                ]
            finally:
                db.close()
        except Exception as e:
            # If database query fails, fall back to empty list
            print(f"Warning: Could not load automation configurations from database: {e}")
            return []
    
    @staticmethod
    def get_time_window() -> tuple:
        """
        Get the time window for matching games
        Returns: (datetime_from, datetime_to)
        """
        # Get first active competition's look_ahead/back settings
        comps = AutomationConfig.get_active_competitions()
        if not comps:
            # Default: look 7 days ahead, 1 day back
            look_ahead = 7
            look_back = 1
        else:
            look_ahead = max(c.get("look_ahead_days", 7) for c in comps)
            look_back = max(c.get("look_back_days", 1) for c in comps)
        
        now = datetime.utcnow()
        time_from = now - timedelta(days=look_back)
        time_to = now + timedelta(days=look_ahead)
        
        return (time_from, time_to)
