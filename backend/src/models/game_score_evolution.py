"""GameScoreEvolution model for storing score progression during periods"""
from sqlalchemy import Column, String, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class GameScoreEvolution(Base, TimestampMixin):
    """
    Stores score evolution during a game period.
    
    Example: "1-0", "2-0", "2-1" at specific frame/timestamp ranges.
    Each score value tracks the frame range when that score was active.
    """
    __tablename__ = 'game_score_evolution'
    
    # Primary key
    id = Column(String(50), primary_key=True, nullable=False)
    
    # Foreign keys
    period_id = Column(Integer, ForeignKey('periods.id'), nullable=False, index=True)
    game_id = Column(String(50), ForeignKey('games.id'), nullable=False, index=True)
    
    # Score representation
    score = Column(String(20), nullable=False)  # e.g., "1-0", "2-1"
    score_home = Column(Integer, nullable=False)
    score_away = Column(Integer, nullable=False)
    
    # Frame range when this score was active
    frame_start = Column(Integer, nullable=False)
    frame_end = Column(Integer, nullable=False)
    
    # Timestamp range when this score was active
    timestamp_start = Column(Float, nullable=False)  # Seconds from period start
    timestamp_end = Column(Float, nullable=False)
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    period = relationship("Period", back_populates="score_evolution")
    game = relationship("Game")
    
    def __repr__(self):
        return f"<GameScoreEvolution(period={self.period_id}, score={self.score}, frames={self.frame_start}-{self.frame_end})>"
