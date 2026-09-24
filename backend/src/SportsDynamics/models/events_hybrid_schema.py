"""
Hybrid Schema Event Models
Tables implementing critical columns + JSONB sections pattern for optimal performance
"""

from uuid import uuid4
from sqlalchemy import Column, String, Integer, Index, ForeignKey, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


# ============================================================================
# EVENTS TABLE - Core Event Records
# ============================================================================

class Events(Base, TimestampMixin):
    """
    Events table with hybrid schema:
    - 12 critical columns (BTREE indexed for fast jointures)
    - 17 JSONB sections (GIN indexed for flexible queries)
    """
    __tablename__ = "events"
    
    # Metadata
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === CRITICAL COLUMNS (BTREE Indexed for jointures) ===
    period_id = Column(Integer, index=True)
    player_id = Column(String(50), ForeignKey("players.id"), index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    opponent_team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    targeted_player_id = Column(String(50), ForeignKey("players.id"))
    goalkeeper_id = Column(String(50), ForeignKey("players.id"))
    expected_defender_at_arrival_id = Column(String(50), ForeignKey("players.id"))
    previous_passer_id = Column(String(50), ForeignKey("players.id"))
    possession_id = Column(UUID, index=True)
    type_of_play_id = Column(UUID, index=True)
    phase_of_play_id = Column(UUID, index=True)
    individual_possession_id = Column(UUID, index=True)
    
    # === JSONB COLUMNS (GIN Indexed for queries) ===
    entity = Column(JSONB)
    time = Column(JSONB)
    phase = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    receiver = Column(JSONB)
    channel = Column(JSONB)
    adds = Column(JSONB)
    pass_data = Column(JSONB)
    custom = Column(JSONB)
    cross = Column(JSONB)
    shot = Column(JSONB)
    boxentry = Column(JSONB)
    finalthirdentry = Column(JSONB)
    clearance = Column(JSONB)
    pressure = Column(JSONB)
    receivingrun = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_events_game_period', 'game_id', 'period_id'),
        Index('idx_events_team_period', 'team_id', 'period_id'),
        Index('idx_events_possession', 'possession_id'),
        Index('idx_events_phase_jointure', 'phase_of_play_id', 'type_of_play_id'),
        Index('idx_events_entity_gin', 'entity', postgresql_using='gin'),
        Index('idx_events_spatial_gin', 'spatial', postgresql_using='gin'),
        Index('idx_events_actors_gin', 'actors', postgresql_using='gin'),
        Index('idx_events_pass_gin', 'pass_data', postgresql_using='gin'),
        Index('idx_events_shot_gin', 'shot', postgresql_using='gin'),
    )


# ============================================================================
# BALL_IN_PLAY TABLE
# ============================================================================

class BallInPlay(Base, TimestampMixin):
    """Ball in play events"""
    __tablename__ = "ball_in_play"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_bip_game_period', 'game_id', 'period_id'),
    )


# ============================================================================
# CARD TABLE
# ============================================================================

class Card(Base, TimestampMixin):
    """Card events (yellow/red)"""
    __tablename__ = "card"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    player_id = Column(String(50), ForeignKey("players.id"), index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    card = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_card_game_period', 'game_id', 'period_id'),
        Index('idx_card_player', 'player_id'),
    )


# ============================================================================
# FOUL TABLE
# ============================================================================

class Foul(Base, TimestampMixin):
    """Foul events"""
    __tablename__ = "foul"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    player_id = Column(String(50), ForeignKey("players.id"), index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    foul = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_foul_game_period', 'game_id', 'period_id'),
        Index('idx_foul_player', 'player_id'),
    )


# ============================================================================
# GOALKICK TABLE
# ============================================================================

class GoalKick(Base, TimestampMixin):
    """Goal kick events"""
    __tablename__ = "goalkick"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    goalkeeper_id = Column(String(50), ForeignKey("players.id"))
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_gk_game_period', 'game_id', 'period_id'),
    )


# ============================================================================
# GOALS TABLE
# ============================================================================

class Goals(Base, TimestampMixin):
    """Goal events"""
    __tablename__ = "goals"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    player_id = Column(String(50), ForeignKey("players.id"), index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    shot = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_goals_game_period', 'game_id', 'period_id'),
        Index('idx_goals_player', 'player_id'),
        Index('idx_goals_team', 'team_id'),
    )


# ============================================================================
# INDIVIDUAL_POSSESSION TABLE
# ============================================================================

class IndividualPossession(Base, TimestampMixin):
    """Individual possession events"""
    __tablename__ = "individual_possession"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    player_id = Column(String(50), ForeignKey("players.id"), index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    phase = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_indposs_game_period', 'game_id', 'period_id'),
        Index('idx_indposs_player', 'player_id'),
    )


# ============================================================================
# KICKOFF TABLE
# ============================================================================

class Kickoff(Base, TimestampMixin):
    """Kick-off events"""
    __tablename__ = "kickoff"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_kickoff_game_period', 'game_id', 'period_id'),
    )


# ============================================================================
# OFFSIDE TABLE
# ============================================================================

class Offside(Base, TimestampMixin):
    """Offside events"""
    __tablename__ = "offside"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    player_id = Column(String(50), ForeignKey("players.id"), index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_offside_game_period', 'game_id', 'period_id'),
        Index('idx_offside_player', 'player_id'),
    )


# ============================================================================
# PHASE_OF_PLAY TABLE - PRIMARY JOINTURE
# ============================================================================

class PhaseOfPlay(Base, TimestampMixin):
    """Phase of play events with strategic context"""
    __tablename__ = "phase_of_play"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    opponent_team_id = Column(String(50), ForeignKey("teams.id"))
    type_of_play_id = Column(UUID, index=True)
    starting_individual_possession_id = Column(UUID)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    phase = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_phase_game_period', 'game_id', 'period_id'),
        Index('idx_phase_team', 'team_id'),
        Index('idx_phase_type', 'type_of_play_id'),
    )


# ============================================================================
# POSSESSION_COLLECTIVE TABLE - PRIMARY JOINTURE
# ============================================================================

class PossessionCollective(Base, TimestampMixin):
    """Collective possession events"""
    __tablename__ = "possession_collective"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    opponent_team_id = Column(String(50), ForeignKey("teams.id"))
    ball_in_play_id = Column(UUID)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    phase = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    possession = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_poss_game_period', 'game_id', 'period_id'),
        Index('idx_poss_team', 'team_id'),
    )


# ============================================================================
# SETPIECES TABLE - Restructured with Type-Specific JSONB Sections
# ============================================================================

class Setpieces(Base, TimestampMixin):
    """
    Set piece events with hybrid schema and type-specific JSONB sections.
    
    Structure:
    - Critical columns (BTREE indexed): team_id, player_id, gata_display_name, period_id
    - Core JSONB sections (always present): entity, time, spatial, actors, phase, channel
    - Type-specific JSONB (only ONE populated): corner_kick, free_kick, indirect_free_kick, throw_in, direct_throw_in
    
    This allows efficient queries by type while maintaining flexibility for diverse setpiece data.
    """
    __tablename__ = "setpieces"
    
    # Metadata
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # === CRITICAL COLUMNS (BTREE Indexed for fast queries) ===
    period_id = Column(Integer, index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), index=True)
    opponent_team_id = Column(String(50), ForeignKey("teams.id"))
    player_id = Column(String(50), ForeignKey("players.id"), index=True)
    gata_display_name = Column(String(255), index=True)  # Source of truth for type determination
    
    # === CORE JSONB SECTIONS (Always Present) ===
    entity = Column(JSONB)              # id, gata_display_name, type, display_group
    time = Column(JSONB)                # start, end, duration, start_frame, end_frame, start_timestamp
    spatial = Column(JSONB)             # distance, distance_gained, possession_outcome, location
    actors = Column(JSONB)              # player_in_possession, team, opponent_team, players_involved
    phase = Column(JSONB)               # phase, phase_time, min:sec, possession_chain
    channel = Column(JSONB)             # channel, side, field_zone, area
    
    # === TYPE-SPECIFIC JSONB SECTIONS (Only ONE Populated Per Record) ===
    corner_kick = Column(JSONB)         # Type: CORNER_KICK
    free_kick = Column(JSONB)           # Type: FREE_KICK
    indirect_free_kick = Column(JSONB)  # Type: INDIRECT_FREE_KICK
    throw_in = Column(JSONB)            # Type: THROW_IN
    direct_throw_in = Column(JSONB)     # Type: DIRECT_THROW_IN
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    team = relationship("Team", foreign_keys=[team_id], primaryjoin="Setpieces.team_id==Team.id")
    opponent_team_rel = relationship("Team", foreign_keys=[opponent_team_id], primaryjoin="Setpieces.opponent_team_id==Team.id")
    player = relationship("Player", foreign_keys=[player_id], primaryjoin="Setpieces.player_id==Player.id")
    
    __table_args__ = (
        # Critical column indices
        Index('idx_setpiece_game_period', 'game_id', 'period_id'),
        Index('idx_setpiece_team_period', 'team_id', 'period_id'),
        Index('idx_setpiece_gata_type', 'gata_display_name'),  # Type filtering
        # JSONB indices
        Index('idx_setpiece_entity_gin', 'entity', postgresql_using='gin'),
        Index('idx_setpiece_spatial_gin', 'spatial', postgresql_using='gin'),
        Index('idx_setpiece_actors_gin', 'actors', postgresql_using='gin'),
        Index('idx_setpiece_corner_gin', 'corner_kick', postgresql_using='gin'),
        Index('idx_setpiece_freekick_gin', 'free_kick', postgresql_using='gin'),
        Index('idx_setpiece_throwin_gin', 'throw_in', postgresql_using='gin'),
    )
    
    def get_type_specific_section(self):
        """Returns (type_name, type_data) tuple for the active type section, or (None, None) if none"""
        if self.corner_kick:
            return ("corner_kick", self.corner_kick)
        elif self.free_kick:
            return ("free_kick", self.free_kick)
        elif self.indirect_free_kick:
            return ("indirect_free_kick", self.indirect_free_kick)
        elif self.throw_in:
            return ("throw_in", self.throw_in)
        elif self.direct_throw_in:
            return ("direct_throw_in", self.direct_throw_in)
        return (None, None)
    
    def to_dict(self):
        """Serialize entire setpiece record to dictionary"""
        return {
            "id": str(self.id),
            "game_id": self.game_id,
            "period_id": self.period_id,
            "team_id": self.team_id,
            "opponent_team_id": self.opponent_team_id,
            "player_id": self.player_id,
            "gata_display_name": self.gata_display_name,
            "entity": self.entity,
            "time": self.time,
            "spatial": self.spatial,
            "actors": self.actors,
            "phase": self.phase,
            "channel": self.channel,
            "corner_kick": self.corner_kick,
            "free_kick": self.free_kick,
            "indirect_free_kick": self.indirect_free_kick,
            "throw_in": self.throw_in,
            "direct_throw_in": self.direct_throw_in,
        }


# ============================================================================
# TYPE_OF_PLAY TABLE
# ============================================================================

class TypeOfPlay(Base, TimestampMixin):
    """Type of play classification"""
    __tablename__ = "type_of_play"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, index=True)
    
    entity = Column(JSONB)
    time = Column(JSONB)
    spatial = Column(JSONB)
    actors = Column(JSONB)
    type_of_play = Column(JSONB)
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id], passive_deletes=True)
    
    __table_args__ = (
        Index('idx_top_game_period', 'game_id', 'period_id'),
    )
