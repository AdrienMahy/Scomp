"""Lineup_Player model for storing individual player participation in a lineup"""
from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class LineupPlayer(Base, TimestampMixin):
    """
    Stores player participation in a team lineup for a game
    
    Each row = player in a specific lineup (game/team)
    Maps to metadata.json players array with full participation data
    """
    __tablename__ = 'lineup_players'
    
    # Primary key - MUST be String(200) to match migration 007
    id = Column(String(200), primary_key=True, nullable=False)
    
    # Foreign keys
    lineup_team_id = Column(String(200), ForeignKey('lineup_teams.id'), nullable=False, index=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    
    # Player role in lineup (JSON: "starter")
    starting = Column(Boolean, nullable=True)
    
    # Substitute status (JSON: "substitute")
    is_substitute = Column(Boolean, nullable=True, default=False)
    
    # Position info (JSON: "position" - e.g., "DEF", "MID", "FWD")
    position = Column(String(50), nullable=True)
    
    # Jersey number (JSON: "jersey")
    shirt_number = Column(Integer, nullable=True)
    
    # Playing time in minutes (JSON: "playing_time")
    playing_time = Column(Float, nullable=True)
    
    # Individual possession percentage (JSON: "individual_possession")
    individual_possession = Column(Float, nullable=True)
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    lineup_team = relationship("LineupTeam", back_populates="lineup_players")
    player = relationship("Player", back_populates="lineup_players")
    
    def __repr__(self):
        return f"<LineupPlayer player={self.player_id} starting={self.starting} jersey={self.shirt_number} playing_time={self.playing_time}>"
