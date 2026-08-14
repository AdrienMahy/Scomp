"""SportsDynamics scraper implementation"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
import logging

from .base_scraper import BaseScraper
from .transformers import transform_game, transform_team, transform_club, transform_player
from ..api import SportsDynamicsClient
from ..models import Game, Team, Club, Player, Period, Squad

logger = logging.getLogger(__name__)


class SportsDynamicsScraper(BaseScraper):
    """SportsDynamics API scraper"""
    
    def __init__(self, api_key: str = None, api_url: str = None):
        """Initialize scraper with API client"""
        self.client = SportsDynamicsClient(api_key, api_url)
    
    def scrape_competition(self, competition_id: str, season_id: str, db: Session) -> Dict[str, Any]:
        """
        Scrape complete competition (games, teams, players)
        
        Args:
            competition_id: Competition ID
            season_id: Season ID
            db: Database session
            
        Returns:
            Dict with counts of scraped items
        """
        result = {
            "games": 0,
            "teams": 0,
            "players": 0,
            "errors": []
        }
        
        try:
            # Scrape games
            game_ids = self.scrape_games(competition_id, season_id, db)
            result["games"] = len(game_ids)
            
            logger.info(f"Scraped {result['games']} games for {competition_id}/{season_id}")
            
        except Exception as e:
            logger.error(f"Error scraping competition {competition_id}: {e}")
            result["errors"].append(str(e))
        
        return result
    
    def scrape_games(self, competition_id: str, season_id: str, db: Session) -> List[str]:
        """
        Scrape all games for a season
        
        Args:
            competition_id: Competition ID
            season_id: Season ID
            db: Database session
            
        Returns:
            List of scraped game IDs
        """
        game_ids = []
        
        try:
            # Get games from API
            api_games = self.client.get_games(competition_id, season_id)
            
            for api_game in api_games:
                try:
                    # Transform and save game
                    game = transform_game(api_game, competition_id, season_id)
                    
                    # Check if exists
                    existing = db.query(Game).filter(Game.id == game.id).first()
                    if existing:
                        # Update
                        for key, value in game.__dict__.items():
                            if not key.startswith("_"):
                                setattr(existing, key, value)
                        game = existing
                    else:
                        db.add(game)
                    
                    # Process teams
                    self._scrape_game_teams(api_game, db)
                    
                    # Process periods
                    self._scrape_periods(api_game, game.id, db)
                    
                    # Process squads
                    self._scrape_squads(api_game, game.id, db)
                    
                    game_ids.append(game.id)
                    
                except Exception as e:
                    logger.error(f"Error processing game {api_game.get('id')}: {e}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error scraping games: {e}")
            db.rollback()
            raise
        
        return game_ids
    
    def _scrape_game_teams(self, api_game: Dict[str, Any], db: Session) -> None:
        """Scrape and store teams from game"""
        for team_key in ["homeTeam", "awayTeam"]:
            api_team = api_game.get(team_key, {})
            if api_team.get("id"):
                team = transform_team(api_team)
                
                existing = db.query(Team).filter(Team.id == team.id).first()
                if not existing:
                    db.add(team)
    
    def _scrape_periods(self, api_game: Dict[str, Any], game_id: str, db: Session) -> None:
        """Scrape and store game periods"""
        for api_period in api_game.get("periods", []):
            period = Period(
                id=api_period.get("id", f"{game_id}_period_{api_period.get('periodId')}"),
                game_id=game_id,
                period_id=api_period.get("periodId"),
                start_time=api_period.get("periodStartTime"),
                end_time=api_period.get("periodEndTime")
            )
            
            existing = db.query(Period).filter(Period.id == period.id).first()
            if not existing:
                db.add(period)
    
    def _scrape_squads(self, api_game: Dict[str, Any], game_id: str, db: Session) -> None:
        """Scrape and store game squads (players)"""
        for api_squad in api_game.get("squads", []):
            team_id = api_squad.get("teamId")
            squad_id = f"{game_id}_squad_{team_id}"
            
            squad = Squad(
                id=squad_id,
                game_id=game_id,
                team_id=team_id,
                raw_data=api_squad
            )
            
            existing = db.query(Squad).filter(Squad.id == squad.id).first()
            if not existing:
                db.add(squad)
            
            # Scrape players from squad
            for api_player in api_squad.get("players", {}).get("items", []):
                player = transform_player(api_player, team_id)
                
                existing_player = db.query(Player).filter(Player.id == player.id).first()
                if not existing_player:
                    db.add(player)
