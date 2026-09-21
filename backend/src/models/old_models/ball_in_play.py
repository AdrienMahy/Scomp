"""Ball In Play model - Root container for continuous ball sequence"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, UUID, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class BallInPlay(Base, TimestampMixin):
    """
    Represents a continuous period when the ball is in play.
    Root entity of RGD hierarchy.
    
    Cardinality: 1 Game → N Ball In Play (104 per game avg)
                 1 BIP → N Possession Collective (1.79 per BIP)
    """
    __tablename__ = "ball_in_play"
    
    # Primary Key
    id = Column(UUID, primary_key=True, default=uuid4)
    
    # Foreign Keys
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    
    # Unique Reference (RGD sequence ID)
    sequence_id = Column(UUID, nullable=False, unique=True)
    
    # Identification
    period_id = Column(Integer, nullable=False)
    
    # Timing (frames)
    start_frame = Column(Integer, nullable=False)
    end_frame = Column(Integer, nullable=False)
    
    # Status
    outcome = Column(String(50))  # 'BALL_OUT_OF_PLAY', 'IN_PLAY', etc.
    
    # Relationships
    game = relationship("Game", back_populates="ball_in_plays")
    possessions_collective = relationship(
        "PossessionCollective",
        back_populates="ball_in_play",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("start_frame < end_frame", name="check_bip_frames_order"),
    )
    
    def __repr__(self):
        return f"<BallInPlay(id={self.id}, game_id={self.game_id}, period={self.period_id}, frames={self.start_frame}-{self.end_frame})>"
