"""Player Distance Covered Models for game performance metrics"""
from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class PlayerDistanceCovered(Base, TimestampMixin):
    """
    Player distance metrics grouped by match and time interval.
    """
    
    __tablename__ = "player_distance_covered"
    
    id = Column(String(36), primary_key=True)
    game_id = Column(String(36), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(String(36), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    
    match_data = Column(JSONB, nullable=False, default=dict)
    intervals = Column(JSONB, nullable=False, default=dict)
    
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
            f"distance={self.match_data.get('total_distance_m', 'N/A')}m>"
        )
