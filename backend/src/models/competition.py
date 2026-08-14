"""Competition and Season models"""
from sqlalchemy import Column, String, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Competition(Base, TimestampMixin):
    """Competition model (e.g., Ligue 1, Ligue 2)"""
    __tablename__ = "competitions"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)  # "SportsDynamics", "Perform", "SecondSpectrum"
    
    # Relationships
    seasons = relationship("Season", back_populates="competition", cascade="all, delete-orphan")
    games = relationship("Game", back_populates="competition", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Competition(id={self.id}, name={self.name}, provider={self.provider})>"


class Season(Base, TimestampMixin):
    """Season model"""
    __tablename__ = "seasons"
    
    id = Column(String(50), primary_key=True)
    competition_id = Column(String(50), ForeignKey("competitions.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g., "2024 - 2025"
    season_year = Column(Integer)  # e.g., 2024
    
    # Metadata
    raw_data = Column(JSON)  # Store provider-specific fields
    
    # Relationships
    competition = relationship("Competition", back_populates="seasons")
    games = relationship("Game", back_populates="season", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Season(id={self.id}, name={self.name})>"
