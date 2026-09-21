"""Type of Play model - Play classification (Structured, Fast, Counter-Attack)"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, UUID, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class TypeOfPlay(Base, TimestampMixin):
    """
    Represents classification of possession type.
    
    Play types:
    - STRUCTURED_PLAY: Organized buildup
    - FAST_PLAY: Quick transition
    - COUNTER_ATTACK: Attacking counter
    
    Cardinality: N Types → 1 Possession (1.13 per Possession)
                 1 Type → N Phases of Play
                 1 Type → N RGD Events (optional ref, 57% populated)
    """
    __tablename__ = "types_of_play"
    
    # Primary Key
    id = Column(UUID, primary_key=True, default=uuid4)
    
    # Foreign Keys (all mandatory)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    possession_collective_id = Column(UUID, ForeignKey("possession_collective.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    # Identification
    period_id = Column(Integer, nullable=False)
    play_type = Column(
        String(50),
        nullable=False
    )  # STRUCTURED_PLAY, FAST_PLAY, COUNTER_ATTACK
    
    # Timing (frames)
    start_frame = Column(Integer, nullable=False)
    end_frame = Column(Integer, nullable=False)
    duration = Column(Float)  # seconds
    
    # Statistics
    n_events = Column(Integer)
    n_passes = Column(Integer)
    distance_gained = Column(Float)
    sequence_xg = Column(Float)  # expected goals
    
    # Outcome
    outcome = Column(String(50))
    goal_in_sequence = Column(Boolean, default=False)
    shot_in_sequence = Column(Boolean, default=False)
    
    # Relationships
    game = relationship("Game", back_populates="types_of_play")
    possession_collective = relationship("PossessionCollective", back_populates="types_of_play")
    team = relationship("Team")
    
    phases_of_play = relationship(
        "PhaseOfPlay",
        back_populates="type_of_play",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("start_frame < end_frame", name="check_top_frames_order"),
        CheckConstraint(
            "play_type IN ('STRUCTURED_PLAY', 'FAST_PLAY', 'COUNTER_ATTACK')",
            name="check_valid_play_type"
        ),
    )
    
    def __repr__(self):
        return f"<TypeOfPlay(id={self.id}, possession_id={self.possession_collective_id}, play_type={self.play_type}, frames={self.start_frame}-{self.end_frame})>"
