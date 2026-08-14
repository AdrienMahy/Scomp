"""Lineup_Player model for storing individual player participation in a lineup"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class LineupPlayer(Base, TimestampMixin):
    """
    Stores player participation in a team lineup for a game
    
    Each row = player in a specific lineup (game/team)
    """
    __tablename__ = 'lineup_players'
    
    # Primary key (auto-increment integer)
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    lineup_team_id = Column(String(200), ForeignKey('lineup_teams.id'), nullable=False, index=True)
    player_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    
    # Player role in lineup
    is_starting = Column(Boolean, default=False)
    is_captain = Column(Boolean, default=False)
    
    # Formation info
    formation_field = Column(String(50), nullable=True)  # e.g., "DEF", "MID", "FWD"
    formation_position = Column(Integer, nullable=True)  # Position number in formation
    
    # Jersey and time
    jersey_number = Column(Integer, nullable=True)
    playing_time = Column(Integer, nullable=True)  # Minutes played
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    lineup_team = relationship("LineupTeam", back_populates="lineup_players")
    player = relationship("Player", back_populates="lineup_players")
    
    def __repr__(self):
        return f"<LineupPlayer player={self.player_id} starting={self.is_starting} jersey={self.jersey_number}>"
