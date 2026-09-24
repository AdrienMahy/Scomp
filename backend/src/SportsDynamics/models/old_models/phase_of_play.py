"""Phase of Play model - Tactical phase within Type of Play"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, UUID, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class PhaseOfPlay(Base, TimestampMixin):
    """
    Represents tactical phase within a Type of Play.
    
    Phase types:
    - ATTACK_VS_MID_BLOCK: Attacking mid-block defense
    - ATTACK_VS_HIGH_BLOCK: Attacking high-block defense
    - ATTACK_VS_LOW_BLOCK: Attacking low-block defense
    - ATTACK_VS_INDIVIDUAL: Attacking individual marking
    - DEFENSIVE: Defensive phase
    - TRANSITION: Transition phase
    
    Cardinality: N Phases → 1 Type of Play (required)
                 N Phases → 1 Possession (optional, can be NULL for 43%)
                 1 Phase → N RGD Events (optional ref, 57% populated)
    """
    __tablename__ = "phases_of_play"
    
    # Primary Key
    id = Column(UUID, primary_key=True, default=uuid4)
    
    # Foreign Keys
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    type_of_play_id = Column(UUID, ForeignKey("types_of_play.id", ondelete="CASCADE"), nullable=False)
    possession_collective_id = Column(UUID, ForeignKey("possession_collective.id", ondelete="CASCADE"), nullable=True)  # Optional
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    # Identification
    period_id = Column(Integer, nullable=False)
    phase_type = Column(String(100), nullable=False)
    # ATTACK_VS_MID_BLOCK, ATTACK_VS_HIGH_BLOCK, ATTACK_VS_LOW_BLOCK, ATTACK_VS_INDIVIDUAL, DEFENSIVE, TRANSITION
    phase_label = Column(String(255))
    
    # Defensive Context
    defensive_block_type = Column(String(20))  # MID, HIGH, LOW
    defensive_block_area = Column(String(100))
    defensive_block_depth = Column(Float)
    
    # Timing (frames)
    start_frame = Column(Integer, nullable=False)
    end_frame = Column(Integer, nullable=False)
    duration = Column(Float)  # seconds
    
    # Outcome
    outcome = Column(String(100))
    goal_in_sequence = Column(Boolean, default=False)
    shot_in_sequence = Column(Boolean, default=False)
    
    # Relationships
    game = relationship("Game", back_populates="phases_of_play")
    type_of_play = relationship("TypeOfPlay", back_populates="phases_of_play")
    possession_collective = relationship("PossessionCollective")
    team = relationship("Team")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("start_frame < end_frame", name="check_pop_frames_order"),
        CheckConstraint(
            "phase_type IN ('ATTACK_VS_MID_BLOCK', 'ATTACK_VS_HIGH_BLOCK', 'ATTACK_VS_LOW_BLOCK', 'ATTACK_VS_INDIVIDUAL', 'DEFENSIVE', 'TRANSITION')",
            name="check_valid_phase_type"
        ),
    )
    
    def __repr__(self):
        return f"<PhaseOfPlay(id={self.id}, type_id={self.type_of_play_id}, phase_type={self.phase_type}, frames={self.start_frame}-{self.end_frame})>"
