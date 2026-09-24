"""Automation configuration model"""
from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import uuid


class AutomationConfiguration(Base, TimestampMixin):
    """
    Automation configuration for scraping schedules.
    Each config represents a scheduled scraping job for a specific competition/season.
    """
    __tablename__ = "automation_configurations"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info
    name = Column(String(255), nullable=False)  # e.g., "Ligue 2 2026-2027"
    description = Column(String(1024))  # Optional description
    
    # Competition & Season
    competition_id = Column(String(50), nullable=False)  # e.g., "comp-ligue2-2024"
    competition_name = Column(String(255), nullable=False)  # e.g., "Ligue 2"
    season_id = Column(String(50), nullable=False)  # e.g., "2026"
    season_name = Column(String(255), nullable=True)  # e.g., "2026 - 2027"
    
    # Provider
    provider = Column(String(50), default="sportsdynamics", nullable=False)
    
    # Scraping schedule
    scrape_interval_minutes = Column(Integer, default=20, nullable=False)  # How often to scrape
    enabled = Column(Boolean, default=True, nullable=False)  # Enable/disable this config
    window_start_utc = Column(String(8), default="00:00:00", nullable=False)
    window_end_utc = Column(String(8), default="23:59:59", nullable=False)
    weekdays = Column(String(20), default="0,1,2,3,4,5,6", nullable=False)
    
    # Time windows
    look_ahead_days = Column(Integer, default=7, nullable=False)  # Future games to scrape
    look_back_days = Column(Integer, default=1, nullable=False)  # Past games to re-check
    live_game_window_minutes = Column(Integer, default=120, nullable=False)  # "Live" game threshold
    
    # Task management
    task_timeout_seconds = Column(Integer, default=30 * 60, nullable=False)  # 30 minutes default
    
    def __repr__(self):
        return f"<AutomationConfiguration(id={self.id}, name={self.name}, enabled={self.enabled})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "competition_id": self.competition_id,
            "competition_name": self.competition_name,
            "season_id": self.season_id,
            "season_name": self.season_name,
            "provider": self.provider,
            "scrape_interval_minutes": self.scrape_interval_minutes,
            "enabled": self.enabled,
            "window_start_utc": self.window_start_utc,
            "window_end_utc": self.window_end_utc,
            "weekdays": [int(day) for day in (self.weekdays or "").split(",") if day != ""],
            "look_ahead_days": self.look_ahead_days,
            "look_back_days": self.look_back_days,
            "live_game_window_minutes": self.live_game_window_minutes,
            "task_timeout_seconds": self.task_timeout_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
