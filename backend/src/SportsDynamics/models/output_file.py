"""OutputFile model for storing game output files and URLs"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class OutputFile(Base, TimestampMixin):
    """
    Stores individual output files for games
    
    Replaces storing full outputFiles array in GameStatus
    Allows querying files by type, status, etc.
    """
    __tablename__ = 'output_files'
    
    # Primary key
    id = Column(String(50), primary_key=True, nullable=False)  # From API
    
    # Foreign key
    game_id = Column(String(50), ForeignKey('games.id'), nullable=False, index=True)
    
    # File information
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # e.g., "mp4", "pdf", "json"
    version = Column(Integer, nullable=True)
    
    # Status tracking
    is_outdated = Column(Boolean, default=False)
    
    # URL and metadata
    url = Column(Text, nullable=True)  # S3 URL (can be long)
    file_size = Column(String(50), nullable=True)  # e.g., "298.96 KB", "11.28 MB"
    file_name_raw = Column(String(255), nullable=True)  # Original name from file.name
    
    # Processing status
    available = Column(Boolean, default=True)
    downloaded_at = Column(DateTime, nullable=True)
    
    # Timestamps (from mixin)
    # created_at: TIMESTAMP
    # updated_at: TIMESTAMP
    
    # Relationships
    game = relationship('Game', back_populates='output_files')
    
    def __repr__(self):
        return f"<OutputFile {self.file_name} ({self.file_type})>"
    
    @property
    def display_name(self):
        """Return human-readable file name"""
        return self.file_name_raw or self.file_name
