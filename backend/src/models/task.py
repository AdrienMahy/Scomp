"""Scraping task tracking model"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Integer, Enum
import enum
from .base import Base, TimestampMixin


class TaskStatus(str, enum.Enum):
    """Task status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapingTask(Base, TimestampMixin):
    """Scraping task for tracking progress"""
    __tablename__ = "scraping_tasks"
    
    id = Column(String(50), primary_key=True)
    
    provider = Column(String(50), nullable=False)  # "SportsDynamics", etc.
    competition_id = Column(String(50), nullable=False, index=True)
    season_id = Column(String(50), nullable=False, index=True)
    
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    
    # Progress tracking
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Metadata
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(String(1000))
    
    extra_metadata = Column(JSON)  # Additional info (renamed from 'metadata')
    
    def __repr__(self):
        return f"<ScrapingTask(id={self.id}, status={self.status})>"
    
    @property
    def progress_percent(self) -> float:
        """Get progress percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
