"""Individual Possession - Player action within a game"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, UUID, CheckConstraint
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class IndividualPossession(Base, TimestampMixin):
    """
    Individual Possession - Represents a player's possession action/event.
    
    A possession is a distinct action where a player controls the ball.
    Multiple possessions can occur within a single PossessionCollective (team possession).
    
    Relationships:
    - 1 Game → N IndividualPossession
    - 1 Team → N IndividualPossession (player's team)
    - 1 Team → N IndividualPossession (opponent team)
    - 1 Player → N IndividualPossession (player_in_possession)
    - 1 IndividualPossession → N RGDEvent (as various roles: actor, receiver, etc.)
    
    Cardinality: ~1,066 possessions per game
    """
    __tablename__ = "individual_possession"
    
    # Primary Key
    id = Column(UUID, primary_key=True, default=uuid4)
    sequence_id = Column(UUID, unique=True, nullable=False, index=True)
    
    # Foreign Keys
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(String(50), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    opponent_team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    # Temporal Data
    period_id = Column(Integer, nullable=False, index=True)
    start_frame = Column(Integer, nullable=False)
    end_frame = Column(Integer, nullable=False)
    start_timestamp = Column(Float, nullable=True)  # Seconds from period start
    end_timestamp = Column(Float, nullable=True)
    duration = Column(Float, nullable=True)
    
    # Physical Data
    distance = Column(Float, nullable=True)
    distance_gained = Column(Float, nullable=True)
    distance_gained_pct = Column(Float, nullable=True)
    progressive_carry = Column(Boolean, nullable=False, server_default="0")
    
    # Audit
    # created_at, updated_at from TimestampMixin
    
    # Constraints
    __table_args__ = (
        CheckConstraint("start_frame < end_frame", name="check_ip_frames_order"),
    )
    
    # Relationships - Game
    game = relationship("Game", back_populates="individual_possessions")
    
    # Relationships - Teams
    team = relationship("Team", foreign_keys=[team_id], back_populates="individual_possessions")
    opponent_team = relationship("Team", foreign_keys=[opponent_team_id])
    
    # Relationships - Player
    player = relationship("Player", back_populates="individual_possessions")
    
    # Relationships - RGD Events (Multiple roles)
    # Each event can reference this IP in different contexts:
    events_as_entry = relationship(
        "RGDEvent",
        foreign_keys="RGDEvent.entry_individual_possession_id",
        back_populates="entry_individual_possession",
        cascade="all, delete-orphan"
    )
    
    events_as_actor = relationship(
        "RGDEvent",
        foreign_keys="RGDEvent.individual_possession_id",
        back_populates="individual_possession",
        cascade="all, delete-orphan"
    )
    
    events_as_last = relationship(
        "RGDEvent",
        foreign_keys="RGDEvent.last_individual_possession_id",
        back_populates="last_individual_possession"
    )
    
    events_as_next = relationship(
        "RGDEvent",
        foreign_keys="RGDEvent.next_individual_possession_id",
        back_populates="next_individual_possession"
    )
    
    events_as_receiver = relationship(
        "RGDEvent",
        foreign_keys="RGDEvent.receiver_individual_possession_id",
        back_populates="receiver_individual_possession",
        cascade="all, delete-orphan"
    )
    
    events_as_starting = relationship(
        "RGDEvent",
        foreign_keys="RGDEvent.starting_individual_possession_id",
        back_populates="starting_individual_possession"
    )
    
    events_as_teammate = relationship(
        "RGDEvent",
        foreign_keys="RGDEvent.teammate_individual_possession_id",
        back_populates="teammate_individual_possession"
    )
    
    def __repr__(self):
        return f"<IndividualPossession(id={self.id}, player={self.player_id}, frames={self.start_frame}-{self.end_frame})>"
