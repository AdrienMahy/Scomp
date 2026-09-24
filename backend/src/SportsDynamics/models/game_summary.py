"""Game summary model - denormalized view of key match information"""
from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base, TimestampMixin


class GameSummary(Base, TimestampMixin):
    """
    Denormalized summary of game with key info and teams
    
    Filled during each game processing
    Structure:
    {
      "id": "...",
      "name": "Nantes vs Red Star",
      "result": "AWAY_TEAM_WIN",
      "startsAt": "2026-08-08T18:45:00Z",
      "playedAt": "2026-08-08T20:15:00Z",
      "round": "1",
      "available": true,  # Match bien traité?
      "teams": [
        {
          "brand": "Nantes",
          "id": "f32406d3-...",
          "side": "HOME",
          "goal": 0,
          "goalconceded": 1,
          "result": "LOSS"  # Relatif à ce team
        },
        {
          "brand": "Red Star",
          "id": "6c3c1394-...",
          "side": "AWAY",
          "goal": 1,
          "goalconceded": 0,
          "result": "WIN"
        }
      ]
    }
    """
    __tablename__ = "game_summary"
    
    game_id = Column(String(50), ForeignKey("games.id"), primary_key=True, nullable=False)
    
    # Main game info
    name = Column(String(255), nullable=False)
    result = Column(String(50))  # "HOME_TEAM_WIN", "AWAY_TEAM_WIN", "DRAW"
    round = Column(String(100))  # "1", "Matchday 5", etc.
    
    # Timestamps
    starts_at = Column(DateTime)
    played_at = Column(DateTime)
    
    # Processing status
    available = Column(Boolean, default=False)  # Match bien traité?
    
    # Teams info - denormalized
    teams = Column(JSONB)  # [{"brand": ..., "id": ..., "side": ..., "goal": ..., "goalconceded": ..., "result": ...}]
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], backref="summary")
    
    def __repr__(self):
        return f"<GameSummary(game_id={self.game_id}, name={self.name}, available={self.available})>"
