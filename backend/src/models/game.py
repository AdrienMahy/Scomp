"""Game, Period, and Squad models"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Game(Base, TimestampMixin):
    """Game/Match model"""
    __tablename__ = "games"
    
    id = Column(String(50), primary_key=True)
    competition_id = Column(String(50), ForeignKey("competitions.id"), nullable=False, index=True)
    season_id = Column(String(50), ForeignKey("seasons.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    result = Column(String(20))  # "MATCH_FINISHED", "NOT_STARTED", etc.
    
    home_team_id = Column(String(50), ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(String(50), ForeignKey("teams.id"), nullable=False)
    
    home_score = Column(Integer)
    away_score = Column(Integer)
    
    home_team_formation = Column(String(50))
    away_team_formation = Column(String(50))
    
    starts_at = Column(DateTime)
    played_at = Column(DateTime)
    
    round_name = Column(String(100))  # "Round 1", "Matchday 5", etc.
    
    # Metadata
    raw_data = Column(JSON)  # Store full API response
    
    # Relationships
    competition = relationship("Competition", back_populates="games")
    season = relationship("Season", back_populates="games")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    periods = relationship("Period", back_populates="game", cascade="all, delete-orphan")
    squads = relationship("Squad", back_populates="game", cascade="all, delete-orphan")
    output_files = relationship("OutputFile", back_populates="game", cascade="all, delete-orphan")
    lineups = relationship("LineupTeam", back_populates="game", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Game(id={self.id}, {self.home_score}-{self.away_score})>"


class Period(Base, TimestampMixin):
    """Game period (1st half, 2nd half, etc.)"""
    __tablename__ = "periods"
    
    id = Column(String(50), primary_key=True)
    game_id = Column(String(50), ForeignKey("games.id"), nullable=False, index=True)
    
    period_id = Column(Integer)  # 1, 2, 3 (OT)
    start_time = Column(Float)  # Relative to match start
    end_time = Column(Float)
    
    # Relationships
    game = relationship("Game", back_populates="periods")
    
    def __repr__(self):
        return f"<Period(id={self.id}, period={self.period_id})>"


class Squad(Base, TimestampMixin):
    """Squad for a team in a game"""
    __tablename__ = "squads"
    
    id = Column(String(50), primary_key=True)
    game_id = Column(String(50), ForeignKey("games.id"), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    
    raw_data = Column(JSON)  # Players list, positions, etc.
    
    # Relationships
    game = relationship("Game", back_populates="squads")
    team = relationship("Team", back_populates="squads")
    
    def __repr__(self):
        return f"<Squad(id={self.id}, team_id={self.team_id})>"
