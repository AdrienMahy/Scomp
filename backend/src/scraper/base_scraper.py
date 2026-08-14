"""Base scraper abstract class"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sqlalchemy.orm import Session


class BaseScraper(ABC):
    """Abstract base class for scrapers"""
    
    @abstractmethod
    def scrape_competition(self, competition_id: str, season_id: str, db: Session) -> Dict[str, Any]:
        """
        Scrape a competition
        
        Args:
            competition_id: Competition ID
            season_id: Season ID
            db: Database session
            
        Returns:
            Scraping result with counts
        """
        pass
    
    @abstractmethod
    def scrape_games(self, competition_id: str, season_id: str, db: Session) -> List[str]:
        """
        Scrape games for competition/season
        
        Args:
            competition_id: Competition ID
            season_id: Season ID
            db: Database session
            
        Returns:
            List of game IDs
        """
        pass
