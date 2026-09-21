"""Pydantic schemas for API responses"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CompetitionRead(BaseModel):
    """Competition response schema"""
    id: str
    name: str
    provider: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class SeasonRead(BaseModel):
    """Season response schema"""
    id: str
    name: str
    season_year: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TeamRead(BaseModel):
    """Team response schema"""
    id: str
    name: str
    brand: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PlayerRead(BaseModel):
    """Player response schema"""
    id: str
    name: str
    first_name: Optional[str]
    last_name: Optional[str]
    jersey_number: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class GameRead(BaseModel):
    """Game response schema"""
    id: str
    name: str
    result: Optional[str]
    home_team_id: str
    away_team_id: str
    home_score: Optional[int]
    away_score: Optional[int]
    starts_at: Optional[datetime]
    played_at: Optional[datetime]
    round_name: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScrapingTaskRead(BaseModel):
    """Scraping task response schema"""
    id: str
    provider: str
    workflow: str
    competition_id: str
    season_id: str
    round_name: Optional[str]
    status: str
    progress_percent: float
    total_items: int
    processed_items: int
    failed_items: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    current_phase: Optional[str]
    current_item_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScrapingTaskCreate(BaseModel):
    """Create scraping task schema"""
    provider: str
    workflow: Optional[str] = "unknown"
    competition_id: str
    season_id: str
    round_name: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class ScrapingLogRead(BaseModel):
    """Scraping log response schema"""
    id: str
    task_id: str
    timestamp: datetime
    level: str
    message: str
    context: Optional[str]
    item_id: Optional[str]
    item_name: Optional[str]
    round: Optional[str]
    stats: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class ScrapingLogCreate(BaseModel):
    """Create scraping log schema"""
    message: str
    level: Optional[str] = "INFO"
    context: Optional[str] = None
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    round: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
