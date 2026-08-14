"""Lineup_Team model for storing team lineups for a specific game"""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class LineupTeam(Base, TimestampMixin):
    """
    Stores team lineup for a specific game
    
    One LineupTeam per game per team (HOME and AWAY)
    Links to all players in that lineup
    """
    __tablename__ = 'lineup_teams'
    
    # Primary key
    id = Column(String(200), primary_key=True, nullable=False)
    
    # Foreign keys
    game_id = Column(String(50), ForeignKey('games.id'), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey('teams.id'), nullable=False, index=True)
    
    # Position in match
    position = Column(String(10), nullable=False)  # 'HOME' or 'AWAY'
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    game = relationship("Game", back_populates="lineups")
    team = relationship("Team", back_populates="lineups")
    lineup_players = relationship("LineupPlayer", back_populates="lineup_team", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LineupTeam game={self.game_id} team={self.team_id} pos={self.position}>"
