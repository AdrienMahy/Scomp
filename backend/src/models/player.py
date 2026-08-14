"""Player model for storing player information"""
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class Player(Base, TimestampMixin):
    """
    Stores player information
    
    Players are deduplicated by ID across all games
    Transfers are detected when a player appears with different teams in different matches
    """
    __tablename__ = 'players'
    
    # Primary key
    id = Column(String(50), primary_key=True, nullable=False)  # From API
    
    # Player info
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    name = Column(String(200), nullable=False)  # Full name
    usage_name = Column(String(200), nullable=True)  # Nickname/usage name
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    lineup_players = relationship("LineupPlayer", back_populates="player", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Player {self.name}>"
