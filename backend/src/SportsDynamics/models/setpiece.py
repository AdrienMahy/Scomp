"""
SQLAlchemy ORM model for Setpieces table

Hybrid schema design:
- Critical columns extracted for BTREE indices (team_id, player_id, gata_display_name)
- Type-specific JSONB sections (only ONE populated per setpiece)
- Flexible JSONB data sections for all other fields
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class Setpiece(Base):
    """
    Represents a single setpiece event in a game.
    
    Structure:
    - Core JSONB sections (always present): entity, time, spatial, actors, phase, channel
    - Type-specific sections (only ONE active): corner_kick, free_kick, indirect_free_kick, throw_in, direct_throw_in
    - Critical extracted columns for fast queries: team_id, player_id, gata_display_name
    
    Example:
        Corner kick: corner_kick JSONB populated, free_kick/throw_in/etc NULL
        Throw-in: throw_in JSONB populated, corner_kick/free_kick/etc NULL
    """
    
    __tablename__ = "setpieces"
    
    # ========================================================================
    # Metadata & Foreign Keys
    # ========================================================================
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ========================================================================
    # Critical Extracted Columns (BTREE Indexed)
    # ========================================================================
    period_id = Column(Integer, nullable=True, index=True)
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    opponent_team_id = Column(String(50), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    player_id = Column(String(50), ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True)
    gata_display_name = Column(String(100), nullable=True, index=True)  # "Free-kick", "Corner kick", etc.
    
    # ========================================================================
    # Core JSONB Sections (Always Present)
    # ========================================================================
    entity = Column(JSONB, nullable=True)  # {type, name, id, gata_display_name}
    time = Column(JSONB, nullable=True)  # {period_id, start, end, duration, start_frame, end_frame, quick_restart, time_to_restart}
    spatial = Column(JSONB, nullable=True)  # {angle, direction, side, corridor, distance, height, start_location, end_location}
    actors = Column(JSONB, nullable=True)  # {player, team, opponent_team, targeted_player, goalkeeper, first_contact_player, players_to_bypass}
    phase = Column(JSONB, nullable=True)  # {possession, type_of_play, phase_of_play, individual_possession, next_individual_possession}
    channel = Column(JSONB, nullable=True)  # {start_channel, end_channel}
    
    # ========================================================================
    # Type-Specific JSONB Sections (Only ONE is populated per setpiece)
    # ========================================================================
    
    # Corner Kick (54 RGD fields)
    corner_kick = Column(JSONB, nullable=True)
    # {type, attackers, defenders, outcome, short, goalkeeper, meta}
    
    # Free-kick (32 RGD fields)
    free_kick = Column(JSONB, nullable=True)
    # {link, meta}
    
    # Indirect Free-kick (54 RGD fields)
    indirect_free_kick = Column(JSONB, nullable=True)
    # {type, link, attackers, outcome, short, meta}
    
    # Throw-in (44 RGD fields)
    throw_in = Column(JSONB, nullable=True)
    # {link, type, attackers, defenders, outcome, meta}
    
    # Direct Throw-in (49 RGD fields)
    direct_throw_in = Column(JSONB, nullable=True)
    # {link, type, outcome, attackers, defenders, short, meta}
    
    # ========================================================================
    # Relationships
    # ========================================================================
    game = relationship("Game", back_populates="setpieces")
    team = relationship("Team", foreign_keys=[team_id])
    opponent_team = relationship("Team", foreign_keys=[opponent_team_id])
    player = relationship("Player", foreign_keys=[player_id])
    
    # ========================================================================
    # Indices
    # ========================================================================
    __table_args__ = (
        Index('idx_setpiece_game_period', 'game_id', 'period_id'),
        Index('idx_setpiece_team_period', 'team_id', 'period_id'),
        Index('idx_setpiece_type', 'gata_display_name'),
        Index('idx_setpiece_player', 'player_id'),
        Index('idx_setpiece_corner_gin', 'corner_kick', postgresql_using='gin'),
        Index('idx_setpiece_freekick_gin', 'free_kick', postgresql_using='gin'),
        Index('idx_setpiece_indirect_gin', 'indirect_free_kick', postgresql_using='gin'),
        Index('idx_setpiece_throwin_gin', 'throw_in', postgresql_using='gin'),
        Index('idx_setpiece_directthrowin_gin', 'direct_throw_in', postgresql_using='gin'),
        Index('idx_setpiece_entity_gin', 'entity', postgresql_using='gin'),
        Index('idx_setpiece_spatial_gin', 'spatial', postgresql_using='gin'),
        Index('idx_setpiece_actors_gin', 'actors', postgresql_using='gin'),
    )
    
    def __repr__(self) -> str:
        return f"<Setpiece(id={self.id}, game={self.game_id}, type={self.gata_display_name}, period={self.period_id})>"
    
    def get_type_specific_section(self) -> tuple[str, dict]:
        """
        Get the active type-specific section and its name.
        
        Returns:
            (section_name, section_data) - e.g., ("corner_kick", {...})
            (None, None) if no type-specific section is populated
        """
        sections = {
            'corner_kick': self.corner_kick,
            'free_kick': self.free_kick,
            'indirect_free_kick': self.indirect_free_kick,
            'throw_in': self.throw_in,
            'direct_throw_in': self.direct_throw_in,
        }
        
        for name, data in sections.items():
            if data is not None:
                return name, data
        
        return None, None
    
    def to_dict(self) -> dict:
        """Convert Setpiece to dictionary representation"""
        type_section, type_data = self.get_type_specific_section()
        
        return {
            'id': self.id,
            'game_id': self.game_id,
            'period_id': self.period_id,
            'team_id': self.team_id,
            'opponent_team_id': self.opponent_team_id,
            'player_id': self.player_id,
            'gata_display_name': self.gata_display_name,
            'entity': self.entity,
            'time': self.time,
            'spatial': self.spatial,
            'actors': self.actors,
            'phase': self.phase,
            'channel': self.channel,
            'type_section': type_section,
            'type_data': type_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
