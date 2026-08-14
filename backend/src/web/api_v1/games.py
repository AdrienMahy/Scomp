"""Games endpoints - scraping and retrieval"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from ...orchestration.scraper_coordinator import ScraperCoordinator
from ...config.filter_config import QueryFilterConfig

router = APIRouter(prefix="/games", tags=["games"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class GamesScrapeRequest(BaseModel):
    """Request body for scraping games"""
    competition_id: str
    season_id: Optional[str] = None
    round_names: Optional[List[str]] = None
    limit: int = 100
    page: int = 1

    class Config:
        schema_extra = {
            "example": {
                "competition_id": "comp-ligue1-2024",
                "season_id": "season-2024-2025",
                "round_names": ["Round 1", "Round 2"],
                "limit": 50,
                "page": 1
            }
        }


class GameResponse(BaseModel):
    """Single game response"""
    id: str
    name: str
    home_score: Optional[int]
    away_score: Optional[int]
    started_at: Optional[str]
    played_at: Optional[str]
    home_team: dict
    away_team: dict
    round: dict
    status: str = "success"


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
    - `competition_id` (required): ID of the competition
    - `season_id` (optional): ID of the season
    - `round_names` (optional): List of round names to filter
    - `limit` (default: 100): Number of games per page
    - `page` (default: 1): Page number
    
    **Example:**
    ```json
    {
        "competition_id": "comp-ligue1-2024",
        "season_id": "season-2024-2025",
        "round_names": ["Round 1", "Round 2"],
        "limit": 50
    }
    ```
    
    **Response:**
    Returns list of games with full details (teams, scores, stats, etc.)
    """
    try:
        # Initialize coordinator
        coordinator = ScraperCoordinator()
        
        # Build filter dictionary
        filters = {
            "available": True,
            "competition_id": request.competition_id,
        }
        
        if request.season_id:
            filters["season_id"] = request.season_id
        
        if request.round_names:
            filters["round"] = request.round_names
        
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
    curl -X GET http://localhost:8000/api/v1/games/scrape/test
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
    curl -X GET http://localhost:8000/api/v1/games/filters
    ```
    """
    filter_config = QueryFilterConfig()
    filters = filter_config.get_predefined_filters("get_games")
    
    return {
        "status": "success",
        "filters": filters,
        "message": "Available filters for get_games"
    }
