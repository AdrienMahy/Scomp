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
    
    round = Column(String(50))  # "1", "2", etc. (filled by scraper)
    round_name = Column(String(100))  # "Round 1", "Matchday 5", etc.
    
    # Metadata
    raw_data = Column(JSON)  # Store full API response
    data_processed = Column(Boolean, default=False, nullable=False)  # True when JSON files downloaded & injected
    
    # Relationships
    competition = relationship("Competition", back_populates="games")
    season = relationship("Season", back_populates="games")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    periods = relationship("Period", back_populates="game", cascade="all, delete-orphan")
    output_files = relationship("OutputFile", back_populates="game", cascade="all, delete-orphan")
    lineups = relationship("LineupTeam", back_populates="game", cascade="all, delete-orphan")
    # Goals and Cards now stored in events table (query with entity type filtering)
    substitutions = relationship("GameSubstitution", back_populates="game", cascade="all, delete-orphan")
    team_distances = relationship("TeamDistanceCovered", back_populates="game", cascade="all, delete-orphan")
    player_distances = relationship("PlayerDistanceCovered", back_populates="game", cascade="all, delete-orphan")
    
    # RGD (Detailed Game Recording) Relationships
    ball_in_plays = relationship("BallInPlay", back_populates="game", cascade="all, delete-orphan")
    possessions_collective = relationship("PossessionCollective", back_populates="game", cascade="all, delete-orphan")
    types_of_play = relationship("TypeOfPlay", back_populates="game", cascade="all, delete-orphan")
    phases_of_play = relationship("PhaseOfPlay", back_populates="game", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Game(id={self.id}, {self.home_score}-{self.away_score})>"


class Period(Base, TimestampMixin):
    """Game period (1st half, 2nd half, etc.)"""
    __tablename__ = "periods"
    
    id = Column(String(50), primary_key=True)
    game_id = Column(String(50), ForeignKey("games.id"), nullable=False, index=True)
    
    # Period number
    period_id = Column(Integer)  # 1, 2, 3 (OT)
    
    # Time information (JSONB)
    # Structure: {"start_frame": int, "end_frame": int, "duration": float}
    time = Column(JSON, nullable=True)
    
    # Team directions (JSONB array)
    # Structure: [
    #   {"team_id": "...", "value": "LTR"/"RTL", "coef": 1/-1},  # home team
    #   {"team_id": "...", "value": "LTR"/"RTL", "coef": 1/-1}   # away team
    # ]
    direction = Column(JSON, nullable=True)
    
    # Relationships
    game = relationship("Game", back_populates="periods")
    score_evolution = relationship("GameScoreEvolution", back_populates="period", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Period(id={self.id}, period={self.period_id})>"
