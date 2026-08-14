"""Games routes - scraping and retrieval"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...config.database import get_db
from ...config.settings import settings
from ...models import Game
from ...orchestration.scraper_coordinator import ScraperCoordinator
from ...config.filter_config import QueryFilterConfig

router = APIRouter(prefix="/games", tags=["games"])


# ============================================================================
# Helper endpoints
# ============================================================================

def get_sportsdynamics_ids(league_name: str, season_name: Optional[str] = None):
    """
    Map league name and season name to SportsDynamics IDs
    
    Args:
        league_name: League name (e.g., "Ligue 1", "Ligue 2")
        season_name: Season name (e.g., "2024 - 2025")
    
    Returns:
        Dict with competitionId and seasonId
        
    Raises:
        ValueError if league or season not found
    """
    ids_config = settings.load_ids_config()
    
    # Find SportsDynamics provider
    sportsdynamics_data = None
    for provider in ids_config:
        if provider.get("Provider") == "SportsDynamics":
            sportsdynamics_data = provider
            break
    
    if not sportsdynamics_data:
        raise ValueError("SportsDynamics configuration not found in ID.json")
    
    # Find league by name
    league = None
    for l in sportsdynamics_data.get("Leagues", []):
        if l.get("Name") == league_name:
            league = l
            break
    
    if not league:
        available_leagues = [l.get("Name") for l in sportsdynamics_data.get("Leagues", [])]
        raise ValueError(f"League '{league_name}' not found. Available: {available_leagues}")
    
    competition_id = league.get("competitionId")
    if not competition_id:
        raise ValueError(f"No competitionId for league {league_name}")
    
    # Find season if specified
    season_id = None
    if season_name:
        season = None
        for s in league.get("Seasons", []):
            if s.get("name") == season_name:
                season = s
                break
        
        if not season:
            available_seasons = [s.get("name") for s in league.get("Seasons", [])]
            raise ValueError(f"Season '{season_name}' not found in {league_name}. Available: {available_seasons}")
        
        season_id = season.get("seasonId")
    
    return {
        "competitionId": competition_id,
        "seasonId": season_id,
        "league_name": league_name,
        "season_name": season_name
    }


@router.get("/ids-config")
async def get_sportsdynamics_ids_endpoint():
    """
    Get available SportsDynamics competition and season IDs from ID.json
    
    **Returns:**
    - List of leagues with competitionId and seasonId for SportsDynamics
    
    **Usage:**
    ```bash
    curl -X GET http://localhost:8001/games/ids-config
    ```
    """
    try:
        ids_config = settings.load_ids_config()
        
        # Extract SportsDynamics section
        sportsdynamics_data = None
        for provider in ids_config:
            if provider.get("Provider") == "SportsDynamics":
                sportsdynamics_data = provider
                break
        
        if not sportsdynamics_data:
            raise HTTPException(status_code=404, detail="SportsDynamics configuration not found in ID.json")
        
        return {
            "provider": "SportsDynamics",
            "leagues": sportsdynamics_data.get("Leagues", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper endpoints
# ============================================================================

class GamesScrapeRequest(BaseModel):
    """Request body for scraping games"""
    league_name: str  # e.g., "Ligue 1" or "Ligue 2"
    season_name: Optional[str] = None  # e.g., "2024 - 2025"
    round: Optional[str] = None  # e.g., "1"
    round_names: Optional[List[str]] = None
    limit: int = 100
    page: int = 1

    model_config = {
        "json_schema_extra": {
            "example": {
                "league_name": "Ligue 1",
                "season_name": "2024 - 2025",
                "round": "1",
                "limit": 50,
                "page": 1
            }
        }
    }


class GamesScrapeResponse(BaseModel):
    """Response for scrape endpoint"""
    status: str
    count: int
    games: List[dict]
    message: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/scrape", response_model=GamesScrapeResponse)
async def scrape_games(request: GamesScrapeRequest):
    """
    Scrape games from SportsDynamics API
    
    **Parameters:**
    - `league_name` (required): Name of the league (e.g., "Ligue 1", "Ligue 2")
    - `season_name` (optional): Name of the season (e.g., "2024 - 2025")
    - `round_names` (optional): List of round names to filter
    - `limit` (default: 100): Number of games per page
    - `page` (default: 1): Page number
    
    **Example:**
    ```json
    {
        "league_name": "Ligue 1",
        "season_name": "2024 - 2025",
        "round_names": ["Round 1", "Round 2"],
        "limit": 50
    }
    ```
    
    **Response:**
    Returns list of games with full details (teams, scores, stats, etc.)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Map league and season names to IDs
        ids_mapping = get_sportsdynamics_ids(request.league_name, request.season_name)
        competition_id = ids_mapping["competitionId"]
        season_id = ids_mapping["seasonId"]
        
        logger.info(f"📊 IDs Mapping:")
        logger.info(f"  - League: {ids_mapping['league_name']}")
        logger.info(f"  - Season: {ids_mapping['season_name']}")
        logger.info(f"  - Competition ID: {competition_id}")
        logger.info(f"  - Season ID: {season_id}")
        
        # Initialize coordinator
        coordinator = ScraperCoordinator()
        
        # Build filter dictionary
        filters = {
            "available": True,
            "competition_id": competition_id,
        }
        
        if season_id:
            filters["season_id"] = season_id
        
        # Handle round filter
        if request.round:
            filters["round"] = [request.round]  # Single round
        elif request.round_names:
            filters["round"] = request.round_names  # Multiple rounds
        
        logger.info(f"🔍 Filter Dictionary (before transformation):")
        for key, value in filters.items():
            logger.info(f"  - {key}: {value}")
        
        # Scrape games
        games = await coordinator.scrape_games(
            filters=filters,
            limit=request.limit,
            page=request.page
        )
        
        return GamesScrapeResponse(
            status="success",
            count=len(games),
            games=games,
            message=f"Successfully scraped {len(games)} games"
        )
        
    except ValueError as e:
        # Filter validation error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.get("/scrape/test")
async def test_scrape():
    """
    Quick test endpoint - scrape a few games without filters
    
    **Usage:**
    ```bash
    curl -X GET http://localhost:8000/games/scrape/test
    ```
    """
    try:
        coordinator = ScraperCoordinator()
        
        # Minimal filters - just available games
        filters = {
            "available": True,
            "competition_id": "comp-ligue1-2024"
        }
        
        games = await coordinator.scrape_games(
            filters=filters,
            limit=5,  # Just 5 for testing
            page=1
        )
        
        return {
            "status": "success",
            "count": len(games),
            "games": games,
            "message": f"Test successful - got {len(games)} games"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters")
async def get_available_filters():
    """
    Get all available filters for get_games query
    
    **Response:**
    Returns filter schema with types, operators, and descriptions
    
    **Usage:**
    ```bash
    curl -X GET http://localhost:8000/games/filters
    ```
    """
    filter_config = QueryFilterConfig()
    filters = filter_config.get_predefined_filters("get_games")
    
    return {
        "status": "success",
        "filters": filters,
        "message": "Available filters for get_games"
    }


@router.get("", response_model=list)
def list_games(
    competition_id: str = Query(None),
    season_id: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List games from database with optional filtering"""
    query = db.query(Game)
    
    if competition_id:
        query = query.filter(Game.competition_id == competition_id)
    if season_id:
        query = query.filter(Game.season_id == season_id)
    
    games = query.offset(skip).limit(limit).all()
    
    # Convert ORM objects to dictionaries
    result = []
    for game in games:
        game_dict = {
            'id': game.id,
            'name': game.name,
            'home_score': game.home_score,
            'away_score': game.away_score,
            'round_name': game.round_name,
            'starts_at': game.starts_at.isoformat() if game.starts_at else None,
            'output_files': [
                {
                    'id': f.id,
                    'file_name': f.file_name,
                    'file_type': f.file_type,
                    'file_size': f.file_size,
                    'version': f.version,
                    'is_outdated': f.is_outdated,
                    'url': f.url
                }
                for f in game.output_files
            ] if game.output_files else []
        }
        result.append(game_dict)
    
    return result


@router.get("/{game_id}")
def get_game(game_id: str, db: Session = Depends(get_db)):
    """Get game by ID from database with lineups"""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Build lineups array
    lineups = []
    if game.lineups:
        for lineup_team in game.lineups:
            team_lineup = {
                'team_id': lineup_team.team_id,
                'position': lineup_team.position,  # HOME or AWAY
                'players': [
                    {
                        'player_id': lp.player_id,
                        'player_name': lp.player.name if lp.player else None,
                        'first_name': lp.player.first_name if lp.player else None,
                        'last_name': lp.player.last_name if lp.player else None,
                        'usage_name': lp.player.usage_name if lp.player else None,
                        'is_starting': lp.is_starting,
                        'is_captain': lp.is_captain,
                        'jersey_number': lp.jersey_number,
                        'formation_field': lp.formation_field,
                        'formation_position': lp.formation_position,
                        'playing_time': lp.playing_time
                    }
                    for lp in lineup_team.lineup_players
                ] if lineup_team.lineup_players else []
            }
            lineups.append(team_lineup)
    
    # Convert ORM object to dictionary
    game_dict = {
        'id': game.id,
        'name': game.name,
        'home_score': game.home_score,
        'away_score': game.away_score,
        'round_name': game.round_name,
        'starts_at': game.starts_at.isoformat() if game.starts_at else None,
        'lineups': lineups,
        'output_files': [
            {
                'id': f.id,
                'file_name': f.file_name,
                'file_type': f.file_type,
                'file_size': f.file_size,
                'version': f.version,
                'is_outdated': f.is_outdated,
                'url': f.url
            }
            for f in game.output_files
        ] if game.output_files else []
    }
    
    return game_dict
