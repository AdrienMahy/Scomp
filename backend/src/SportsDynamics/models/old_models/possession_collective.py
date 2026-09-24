"""Possession Collective model - Team possession within Ball In Play"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, UUID, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class PossessionCollective(Base, TimestampMixin):
    """
    Represents a team's possession within a Ball In Play period.
    Contains multiple Types of Play and tactical events.
    
    Cardinality: N Possession → 1 Ball In Play (1.79 per BIP)
                 1 Possession → N Types of Play (1.13 per Possession)
                 1 Possession → N RGD Events (optional ref, 61% populated)
    """
    __tablename__ = "possession_collective"
    
    # Primary Key
    id = Column(UUID, primary_key=True, default=uuid4)
    
    # Foreign Keys (all mandatory)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    ball_in_play_id = Column(UUID, ForeignKey("ball_in_play.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    opponent_team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    # Identification
    period_id = Column(Integer, nullable=False)
    
    # Timing (frames)
    start_frame = Column(Integer, nullable=False)
    end_frame = Column(Integer, nullable=False)
    duration = Column(Float)  # seconds
    
    # Statistics
    n_events = Column(Integer)
    n_passes = Column(Integer)
    n_passes_category = Column(String(255))
    distance_gained = Column(Float)  # meters
    distance_gained_pct = Column(Float)  # percentage
    
    # Outcome
    possession_outcome = Column(String(50))  # 'LOST', 'TURNOVER', 'PASS_OUT', etc.
    goal_in_sequence = Column(Boolean, default=False)
    shot_in_sequence = Column(Boolean, default=False)
    
    # Tactical
    formation = Column(String(20))  # e.g., '4-2-3-1'
    attacking_style = Column(String(50))
    
    # Relationships
    game = relationship("Game", back_populates="possessions_collective")
    ball_in_play = relationship("BallInPlay", back_populates="possessions_collective")
    team = relationship("Team", foreign_keys=[team_id])
    opponent_team = relationship("Team", foreign_keys=[opponent_team_id])
    
    types_of_play = relationship(
        "TypeOfPlay",
        back_populates="possession_collective",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("start_frame < end_frame", name="check_pc_frames_order"),
    )
    
    def __repr__(self):
        return f"<PossessionCollective(id={self.id}, game_id={self.game_id}, period={self.period_id}, frames={self.start_frame}-{self.end_frame}, n_passes={self.n_passes})>"
