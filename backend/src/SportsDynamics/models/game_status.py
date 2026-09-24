"""Game status tracking model for incremental scraping"""
from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base, TimestampMixin


class GameStatus(Base, TimestampMixin):
    """
    Tracks the status and version of each game's data.
    
    Used for incremental scraping:
    - Check if data changed before re-downloading
    - Store API state (available, statusRgd, etc.)
    - Hash of outputFiles to detect changes
    """
    __tablename__ = "game_status"
    
    game_id = Column(String(50), ForeignKey("games.id"), primary_key=True, nullable=False)
    
    # API state fields
    available = Column(Boolean, default=False)
    is_ugd_available = Column(Boolean, default=False)
    rgd_status = Column(String(50))  # e.g., "PENDING", "READY", "ERROR"
    ugd_status = Column(String(50))  # e.g., "PENDING", "READY", "ERROR"
    
    # outputFiles - stores complete array from API
    # Variable structure per game, so JSONB is perfect
    output_files = Column(JSONB, default=list)
    
    # SHA256 hash of output_files JSON for change detection
    output_files_hash = Column(String(64))
    
    # When this status was last checked/updated from API
    last_checked_at = Column(DateTime)
    status_changed_at = Column(DateTime)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], backref="status")
    
    def __repr__(self):
        return f"<GameStatus(game_id={self.game_id}, available={self.available}, rgd={self.rgd_status})>"
