"""Distance Covered models for team performance metrics"""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class TeamDistanceCovered(Base, TimestampMixin):
    """
    Team distance metrics grouped by match and time interval.
    """
    __tablename__ = 'team_distance_covered'
    
    # Primary key
    id = Column(String(200), primary_key=True, nullable=False)
    
    # Foreign keys
    game_id = Column(String(200), ForeignKey('games.id'), nullable=False, index=True)
    team_id = Column(String(200), ForeignKey('teams.id'), nullable=False, index=True)
    
    match_data = Column(JSONB, nullable=False, default=dict)
    intervals = Column(JSONB, nullable=False, default=dict)
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    game = relationship("Game", back_populates="team_distances")
    team = relationship("Team", back_populates="distances_covered")
    
    def __repr__(self):
        total = self.match_data.get('total_distance_m', 'N/A') if self.match_data else 'N/A'
        return f"<TeamDistanceCovered(game={self.game_id}, team={self.team_id}, distance={total}m)>"
