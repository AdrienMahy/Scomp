"""
Fitness Entities Models - Player fitness run tracking

Hybrid schema: Critical columns (BTREE indexed) + JSONB metadata (GIN indexed)
Relationships to event tables: PossessionCollective, PhaseOfPlay, TypeOfPlay, IndividualPossession
"""

from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, Index, ForeignKey, UUID, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


# ============================================================================
# PLAYER_FITNESS_RUNS TABLE - Main fitness entity
# ============================================================================

class PlayerFitnessRun(Base, TimestampMixin):
    """
    Player fitness run data with hybrid schema.
    
    Critical columns (35): BTREE indexed for fast filtering & jointures
    JSONB metadata: GIN indexed for flexible queries on labels & classifications
    
    Foreign Keys:
    - game_id, player_id, team_id, opponent_team_id (game context)
    - possession_id, phase_of_play_id, type_of_play_id, individual_possession_id (event references)
    """
    __tablename__ = "player_fitness_runs"
    
    # ========================================================================
    # PRIMARY IDENTIFIERS & GAME CONTEXT
    # ========================================================================
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, nullable=False, index=True)
    
    # ========================================================================
    # ACTOR IDs (Foreign Keys to Core Tables) - All are String(50) to match schema
    # ========================================================================
    player_id = Column(String(50), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    opponent_team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    # ========================================================================
    # EVENT REFERENCES (Foreign Keys to Event Tables) - CRITICAL JOINTURES
    # ========================================================================
    possession_id = Column(String(50), ForeignKey("possession_collective.id", ondelete="SET NULL"), index=True, nullable=True)
    phase_of_play_id = Column(String(50), ForeignKey("phase_of_play.id", ondelete="SET NULL"), index=True, nullable=True)
    type_of_play_id = Column(String(50), ForeignKey("type_of_play.id", ondelete="SET NULL"), index=True, nullable=True)
    individual_possession_id = Column(String(50), ForeignKey("individual_possession.id", ondelete="SET NULL"), index=True, nullable=True)
    
    # ========================================================================
    # TIMING METRICS (4 columns)
    # ========================================================================
    start_time_s = Column(Float, nullable=False)
    end_time_s = Column(Float, nullable=False)
    duration_s = Column(Float, nullable=False)
    start_frame = Column(Integer)
    end_frame = Column(Integer)
    
    # ========================================================================
    # DISTANCE METRICS (3 columns)
    # ========================================================================
    distance_m = Column(Float, nullable=False)
    high_speed_distance_m = Column(Float)
    sprint_distance_m = Column(Float)
    
    # ========================================================================
    # SPEED METRICS (5 columns)
    # ========================================================================
    average_speed = Column(Float)
    peak_speed = Column(Float)
    high_speed_duration = Column(Float)
    sprint_duration = Column(Float)
    time_to_peak_speed = Column(Float)
    
    # ========================================================================
    # ACCELERATION METRICS (4 columns)
    # ========================================================================
    acceleration_at_start = Column(Float)
    peak_acceleration = Column(Float)
    peak_deceleration = Column(Float)
    acceleration_intensity = Column(Integer)
    acceleration_intensity_level = Column(String(100))  # ENUM: LOW, CONTROLLED, HIGH_INTENSITY, EXPLOSIVE
    
    # ========================================================================
    # TACTICAL CONTEXT (5 columns)
    # ========================================================================
    context = Column(String(100))  # ENUM: DEFENSIVE, OFFENSIVE
    direction = Column(String(100))  # ENUM: FORWARD, BACKWARD, LATERAL
    phase_of_play_label = Column(String(100))  # Denormalized label
    play_label = Column(String(100))  # Denormalized label (STRUCTURED_PLAY_*, etc)
    possession_label = Column(String(100))  # ENUM: IN_POSSESSION, OUT_OF_POSSESSION
    
    # ========================================================================
    # SPATIAL POSITIONING (8 columns)
    # ========================================================================
    start_x = Column(Float)  # Start X coordinate (m)
    start_y = Column(Float)  # Start Y coordinate (m)
    end_x = Column(Float)  # End X coordinate (m)
    end_y = Column(Float)  # End Y coordinate (m)
    start_third = Column(String(100))  # ENUM: DEFENSIVE_THIRD, MIDDLE_THIRD, OFFENSIVE_THIRD
    end_third = Column(String(100))  # ENUM: DEFENSIVE_THIRD, MIDDLE_THIRD, OFFENSIVE_THIRD
    start_channel = Column(String(100))  # ENUM: LEFT, CENTRAL, RIGHT
    end_channel = Column(String(100))  # ENUM: LEFT, CENTRAL, RIGHT
    
    # ========================================================================
    # BOOLEAN CLASSIFICATIONS (5 columns) - Denormalized flags
    # ========================================================================
    high_speed_run = Column(Boolean, default=False)
    is_receiving_run = Column(Boolean, default=False)
    sprint = Column(Boolean, default=False)
    run_with_ball = Column(Boolean, default=False)
    on_ball_run = Column(Boolean, default=False)
    
    # ========================================================================
    # BOX & ZONE ENTRIES (5 columns)
    # ========================================================================
    defensive_box_entry = Column(Boolean, default=False)
    offensive_box_entry = Column(Boolean, default=False)
    defensive_third_entry = Column(Boolean, default=False)
    offensive_third_entry = Column(Boolean, default=False)
    functional_start_zone = Column(String(100))  # ENUM: CENTRAL_PROGRESSION, etc
    
    # ========================================================================
    # JSONB METADATA - GIN indexed for flexible queries
    # ========================================================================
    # Contains:
    # - sustained_speeds: {0_5s, 1m, 1s, 2m, 2s, 3m, 3s, 5m}
    # - timing: {time_to_moderate_speed, time_to_high_speed, time_to_sprint}
    # - classification: {functional_end_zone, tactical_space_start, tactical_subspace_start, etc}
    # - box_entries: {flags, zones}
    # - tactical_zones: {position analysis}
    # - phase_and_play_ids: {raw IDs from API}
    metadata_json = Column(JSONB, nullable=True)
    
    # ========================================================================
    # RELATIONSHIPS (SQLAlchemy)
    # ========================================================================
    game = relationship("Game", foreign_keys=[game_id])
    player = relationship("Player", foreign_keys=[player_id])
    team = relationship("Team", foreign_keys=[team_id], overlaps="fitness_runs_home")
    opponent_team = relationship("Team", foreign_keys=[opponent_team_id], overlaps="fitness_runs_away")
    
    possession = relationship("PossessionCollective", foreign_keys=[possession_id], overlaps="fitness_runs")
    phase_of_play = relationship("PhaseOfPlay", foreign_keys=[phase_of_play_id], overlaps="fitness_runs")
    type_of_play = relationship("TypeOfPlay", foreign_keys=[type_of_play_id], overlaps="fitness_runs")
    individual_possession = relationship("IndividualPossession", foreign_keys=[individual_possession_id], overlaps="fitness_runs")
    
    # ========================================================================
    # INDEXES
    # ========================================================================
    __table_args__ = (
        # Primary context indexes
        Index('idx_pfr_game_period', 'game_id', 'period_id'),
        Index('idx_pfr_player', 'player_id'),
        Index('idx_pfr_team', 'team_id'),
        
        # Event relationship indexes (CRITICAL for jointures)
        Index('idx_pfr_possession', 'possession_id'),
        Index('idx_pfr_phase_of_play', 'phase_of_play_id'),
        Index('idx_pfr_type_of_play', 'type_of_play_id'),
        Index('idx_pfr_individual_possession', 'individual_possession_id'),
        
        # Tactical analysis indexes
        Index('idx_pfr_context', 'context'),
        Index('idx_pfr_direction', 'direction'),
        Index('idx_pfr_acceleration_level', 'acceleration_intensity_level'),
        
        # Composite indexes for complex queries
        Index('idx_pfr_context_phase', 'context', 'phase_of_play_id'),
        Index('idx_pfr_team_phase', 'team_id', 'phase_of_play_id'),
        Index('idx_pfr_possession_duration', 'possession_id', 'duration_s'),
        Index('idx_pfr_phase_distance', 'phase_of_play_id', 'distance_m'),
        
        # JSONB index for flexible queries
        Index('idx_pfr_metadata_gin', 'metadata_json', postgresql_using='gin'),
    )


# ============================================================================
# PLAYER_FITNESS_SUMMARY TABLE - Optional aggregation
# ============================================================================

class PlayerFitnessSummary(Base, TimestampMixin):
    """
    Aggregated fitness statistics per player per game.
    
    Calculated from PlayerFitnessRun records.
    Used for quick dashboard views without re-aggregating.
    """
    __tablename__ = "player_fitness_summary"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(String(50), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Aggregated metrics
    total_runs = Column(Integer, default=0)
    total_distance_m = Column(Float, default=0.0)
    total_high_speed_distance_m = Column(Float, default=0.0)
    total_sprint_distance_m = Column(Float, default=0.0)
    average_run_speed_ms = Column(Float)
    peak_speed_ms = Column(Float)
    
    # Classification counts
    high_speed_run_count = Column(Integer, default=0)
    sprint_count = Column(Integer, default=0)
    receiving_run_count = Column(Integer, default=0)
    
    # Context distribution
    offensive_runs = Column(Integer, default=0)
    defensive_runs = Column(Integer, default=0)
    
    game = relationship("Game")
    player = relationship("Player")
    team = relationship("Team")
    
    __table_args__ = (
        Index('idx_pfs_game', 'game_id'),
        Index('idx_pfs_player', 'player_id'),
        Index('idx_pfs_team', 'team_id'),
        Index('idx_pfs_game_player', 'game_id', 'player_id'),
    )


# ============================================================================
# TEAM_FITNESS_SUMMARY TABLE - Optional aggregation
# ============================================================================

class TeamFitnessSummary(Base, TimestampMixin):
    """
    Aggregated fitness statistics per team per game.
    
    Calculated from PlayerFitnessRun records grouped by team.
    Used for team-level performance analysis.
    """
    __tablename__ = "team_fitness_summary"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Aggregated metrics
    total_runs = Column(Integer, default=0)
    total_distance_m = Column(Float, default=0.0)
    total_high_speed_distance_m = Column(Float, default=0.0)
    total_sprint_distance_m = Column(Float, default=0.0)
    average_team_speed_ms = Column(Float)
    
    # Players involved
    players_tracked = Column(Integer, default=0)
    
    # Context distribution
    offensive_runs = Column(Integer, default=0)
    defensive_runs = Column(Integer, default=0)
    
    # Performance by phase
    average_runs_per_phase = Column(Float)
    
    game = relationship("Game")
    team = relationship("Team")
    
    __table_args__ = (
        Index('idx_tfs_game', 'game_id'),
        Index('idx_tfs_team', 'team_id'),
        Index('idx_tfs_game_team', 'game_id', 'team_id'),
    )
