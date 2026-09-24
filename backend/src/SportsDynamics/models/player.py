"""Player model for storing player information"""
from sqlalchemy import Column, String, Integer, Date, JSON
from sqlalchemy.dialects.postgresql import JSON as JSONB
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
    
    # Profile
    photo = Column(String(500), nullable=True)  # Photo URL
    age = Column(Integer, nullable=True)  # Player age
    birthdate = Column(Date, nullable=True)  # Birth date
    
    # Current Team (denormalized for quick access)
    current_team_id = Column(String(50), nullable=True)  # Foreign key to Team
    current_team_brand = Column(String(255), nullable=True)  # Team logo/brand
    
    # National Team
    current_national_team_id = Column(String(50), nullable=True)
    current_national_team_brand = Column(String(255), nullable=True)
    
    # Complex data (JSONB for proper operators and indexing)
    nationalities = Column(JSONB, nullable=True)  # List of nationalities with ISO3 codes
    positions = Column(JSONB, nullable=True)  # List of positions with codes and groups
    teams = Column(JSONB, nullable=True)  # Team history tracking: {current_team: {id, brand}, history: [{team_id, team_name, team_brand, round_start, round_end}, ...]}
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    lineup_players = relationship("LineupPlayer", back_populates="player", cascade="all, delete-orphan")
    # Goals and Cards now stored in events table
    substitutions_in = relationship("GameSubstitution", foreign_keys="GameSubstitution.player_in_id", back_populates="player_in")
    substitutions_out = relationship("GameSubstitution", foreign_keys="GameSubstitution.player_out_id", back_populates="player_out")
    distances_covered = relationship("PlayerDistanceCovered", back_populates="player")
    
    def __repr__(self):
        return f"<Player {self.name}>"
    
    # Helper methods for teams tracking
    def set_current_team(self, team_id: str, team_brand: str) -> None:
        """Update current team in teams structure"""
        if self.teams is None:
            self.teams = {"current_team": {}, "history": []}
        self.teams["current_team"] = {"id": team_id, "brand": team_brand}
        # Also update denormalized columns for backward compatibility
        self.current_team_id = team_id
        self.current_team_brand = team_brand
    
    def get_current_team(self) -> dict | None:
        """Get current team from teams structure"""
        if self.teams and "current_team" in self.teams:
            return self.teams["current_team"]
        return None
    
    def add_team_history(self, team_id: str, team_name: str, team_brand: str, 
                         round_start: int, round_end: int) -> None:
        """Add team to history"""
        if self.teams is None:
            self.teams = {"current_team": {}, "history": []}
        if "history" not in self.teams:
            self.teams["history"] = []
        
        self.teams["history"].append({
            "team_id": team_id,
            "team_name": team_name,
            "team_brand": team_brand,
            "round_start": round_start,
            "round_end": round_end
        })
    
    def get_team_history(self) -> list | None:
        """Get team history"""
        if self.teams and "history" in self.teams:
            return self.teams["history"]
        return None
    
    def get_team_at_round(self, round_num: int) -> dict | None:
        """Get team at specific round from history"""
        if not self.teams or "history" not in self.teams:
            return None
        
        for team_record in self.teams["history"]:
            if team_record["round_start"] <= round_num <= team_record["round_end"]:
                return team_record
        return None
