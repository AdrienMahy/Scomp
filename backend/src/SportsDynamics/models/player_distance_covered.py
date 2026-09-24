"""Player Distance Covered Models for game performance metrics"""
from sqlalchemy import Column, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class PlayerDistanceCovered(Base, TimestampMixin):
    """
    Player distance metrics per game with JSONB structure.
    
    Organizes distance breakdowns into logical groups:
    - metrics: total_distance_m, distance_per_min_played_m, minutes_played
    - speed_zones: walking, jogging, moderated_intensity, high_intensity, sprint
    - game_state: in_play, out_of_play
    - time_intervals: {"0_5": 522.02, "5_10": 642.45, ..., "90+": 525.73}
    """
    
    __tablename__ = "player_distance_covered"
    
    id = Column(String(36), primary_key=True)
    game_id = Column(String(36), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(String(36), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # JSONB Columns - New Structure
    # metrics: {total_distance_m, distance_per_min_played_m, minutes_played}
    metrics = Column(JSON, nullable=False)
    
    # speed_zones: {walking, jogging, moderated_intensity, high_intensity, sprint}
    speed_zones = Column(JSON, nullable=False)
    
    # game_state: {in_play, out_of_play}
    game_state = Column(JSON, nullable=False)
    
    # time_intervals: {"0_5": 522.02, "5_10": 642.45, ..., "90+": 525.73}
    time_intervals = Column(JSON, nullable=False)
    
    # Timestamps (from TimestampMixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    game = relationship("Game", back_populates="player_distances")
    player = relationship("Player", back_populates="distances_covered")
    team = relationship("Team", foreign_keys=[team_id])
    
    def __repr__(self):
        return (
            f"<PlayerDistanceCovered game_id={self.game_id} "
            f"player_id={self.player_id} "
            f"distance={self.metrics.get('total_distance_m', 'N/A')}m>"
        )


