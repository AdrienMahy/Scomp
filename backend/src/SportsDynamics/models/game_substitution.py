"""GameSubstitution model for storing player substitutions"""
from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class GameSubstitution(Base, TimestampMixin):
    """
    Stores substitution events for a match.
    
    One substitution per row with player_in, player_out, and timing information.
    """
    __tablename__ = 'game_substitutions'
    
    # Primary key
    id = Column(String(50), primary_key=True, nullable=False)
    
    # Foreign keys
    game_id = Column(String(50), ForeignKey('games.id'), nullable=False, index=True)
    player_in_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    player_out_id = Column(String(50), ForeignKey('players.id'), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey('teams.id'), nullable=False, index=True)
    
    # Match context
    period = Column(Integer, nullable=False)  # 1, 2, etc.
    frame = Column(Integer, nullable=False)   # Frame number in video
    timestamp = Column(Float, nullable=True)  # Timestamp in seconds (from metadata)
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    game = relationship("Game", back_populates="substitutions")
    player_in = relationship("Player", foreign_keys=[player_in_id], back_populates="substitutions_in")
    player_out = relationship("Player", foreign_keys=[player_out_id], back_populates="substitutions_out")
    team = relationship("Team", back_populates="substitutions")
    
    def __repr__(self):
        return f"<GameSubstitution(game={self.game_id}, {self.player_in_id} in / {self.player_out_id} out, period={self.period})>"
