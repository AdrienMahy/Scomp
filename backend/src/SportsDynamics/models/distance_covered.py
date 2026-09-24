"""Distance Covered models for team performance metrics"""
from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class TeamDistanceCovered(Base, TimestampMixin):
    """
    Team distance metrics per game with JSONB structure.
    
    Organizes distance breakdowns into logical groups:
    - metrics: total_distance_m
    - speed_zones: walking, jogging, moderated_intensity, high_intensity, sprint
    - game_state: in_play, out_of_play
    - time_intervals: {"0_5": 7373.12, "5_10": ..., "90+": ...}
    """
    __tablename__ = 'team_distance_covered'
    
    # Primary key
    id = Column(String(200), primary_key=True, nullable=False)
    
    # Foreign keys
    game_id = Column(String(200), ForeignKey('games.id'), nullable=False, index=True)
    team_id = Column(String(200), ForeignKey('teams.id'), nullable=False, index=True)
    
    # JSONB Columns - New Structure
    # metrics: {total_distance_m}
    metrics = Column(JSON, nullable=False)
    
    # speed_zones: {walking, jogging, moderated_intensity, high_intensity, sprint}
    speed_zones = Column(JSON, nullable=False)
    
    # game_state: {in_play, out_of_play}
    game_state = Column(JSON, nullable=False)
    
    # time_intervals: {"0_5": 7373.12, "5_10": ..., "90+": ...}
    time_intervals = Column(JSON, nullable=False)
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    game = relationship("Game", back_populates="team_distances")
    team = relationship("Team", back_populates="distances_covered")
    
    def __repr__(self):
        total = self.metrics.get('total_distance_m', 'N/A') if self.metrics else 'N/A'
        return f"<TeamDistanceCovered(game={self.game_id}, team={self.team_id}, distance={total}m)>"

