"""Scraping logs model for tracking scrape operations"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, JSON
from .base import Base


class ScrapingLog(Base):
    """Individual log entry for a scraping task"""
    __tablename__ = "scraping_logs"
    
    id = Column(String(50), primary_key=True)
    task_id = Column(String(50), nullable=False, index=True)  # Foreign key reference
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    level = Column(String(20), nullable=False, default="INFO")  # DEBUG, INFO, WARNING, ERROR
    
    message = Column(Text, nullable=False)  # Log message
    context = Column(String(100))  # Context (e.g., "game_processing", "api_call", "validation")
    round = Column(String(20), nullable=True)  # Round number (e.g., "1", "J1", "Round 1")
    
    # Optional details for debugging
    item_id = Column(String(50))  # ID of item being processed (game_id, team_id, etc)
    item_name = Column(String(255))  # Name/label of item
    
    # Table-level DELETE/INSERT stats: {"table_name": {"deleted": 0, "inserted": 10}}
    stats = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<ScrapingLog(task_id={self.task_id}, level={self.level}, timestamp={self.timestamp})>"
