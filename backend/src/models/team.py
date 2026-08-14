"""Team and Club models"""
from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Team(Base, TimestampMixin):
    """Team model"""
    __tablename__ = "teams"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(255))  # Brand/official name
    
    # Relationships
    home_games = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")
    squads = relationship("Squad", back_populates="team")
    lineups = relationship("LineupTeam", back_populates="team")
    
    def __repr__(self):
        return f"<Team(id={self.id}, name={self.name})>"


class Club(Base, TimestampMixin):
    """Club model (extended team info)"""
    __tablename__ = "clubs"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(255))
    logo_url = Column(String(500))
    
    # Provider-specific IDs
    provider_ids = Column(JSON)  # { "SecondSpectrum": "...", "Perform": "...", "SportsDynamics": "..." }
    
    raw_data = Column(JSON)
    
    def __repr__(self):
        return f"<Club(id={self.id}, name={self.name})>"
