"""Games routes - scraping and retrieval"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import cast, Integer
from datetime import datetime
import uuid
import logging
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from src.config.database import get_db
from src.config.settings import settings
from src.SportsDynamics.models import Game, Team, Season, ScrapingTask, TaskStatus, ScrapingLog, LineupPlayer
from src.SportsDynamics.orchestration.scraper_coordinator import ScraperCoordinator
from src.SportsDynamics.orchestration.scrape_workflows import (
    initialize_season,
    scrape_round as run_scrape_round,
    scrape_game as run_scrape_game,
    scrape_autonomous as run_scrape_autonomous,
    autonomous_dry_run,
)
from src.SportsDynamics.orchestration.task_tracker import TaskTracker
from src.SportsDynamics.orchestration.task_retention import reconcile_stale_tasks
from src.tasks.scrape_tasks import (
    initialize_season_task,
    scrape_round_task,
    scrape_game_task,
    scrape_autonomous_task,
)
from src.config.filter_config import QueryFilterConfig

router = APIRouter(prefix="/sportsdynamics/games", tags=["sportsdynamics-games"])
logger = logging.getLogger(__name__)


# ============================================================================
# Helper functions
# ============================================================================

def get_game_injection_stats(game_id: str, db: Session) -> dict:
    """
    Get injection statistics for a game (count of rows inserted per table)
    
    Args:
        game_id: ID of the game
        db: Database session
    
    Returns:
        Dict with counts for each table
    """
    try:
        stats = {
            "game_id": game_id,
            "games": 1 if db.query(Game).filter(Game.id == game_id).first() else 0,
            "lineups": db.query(LineupPlayer).filter(LineupPlayer.game_id == game_id).count(),
        }
        return stats
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not fetch game stats for {game_id}: {str(e)}")
        # Return safe defaults instead of error
        return {
            "game_id": game_id,
            "games": 0,
            "goals": 0,
            "cards": 0,
            "lineups": 0,
        }


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


class FullSeasonScrapeRequest(BaseModel):
    """Request body for full season scrape"""
    league_name: str  # e.g., "Ligue 1"
    season_name: Optional[str] = None  # e.g., "2024 - 2025"
    round: Optional[str] = None  # e.g., "1" (optional round filter)
    round_names: Optional[List[str]] = None  # e.g., ["1", "2"]

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


class FullSeasonScrapeResponse(BaseModel):
    """Response for full season scrape endpoint"""
    status: str
    league: str
    season: str
    total_games: int
    message: Optional[str] = None


class ClubsScrapeResponse(BaseModel):
    """Response for clubs scrape endpoint"""
    status: str
    count: int
    updated: int
    clubs: List[dict]
    message: Optional[str] = None


class UnifiedScrapeRequest(BaseModel):
    """Request body for unified scrape endpoint (customizable scrape)"""
    league_name: str                          # e.g., "Ligue 1"
    season_name: Optional[str] = None         # e.g., "2024 - 2025"
    round_names: Optional[List[str]] = None   # Multiple rounds: ["1", "2", "3"]
    available_only: bool = True               # Only games with available files
    mode: str = "weekly"                      # "schedule" or "weekly"

    model_config = {
        "json_schema_extra": {
            "example": {
                "league_name": "Ligue 2",
                "season_name": "2024 - 2025",
                "round_names": ["1", "2", "3"],
                "available_only": True,
                "mode": "weekly"
            }
        }
    }


class UnifiedScrapeResponse(BaseModel):
    """Response for unified scrape endpoint"""
    status: str
    league: str
    season: str
    mode: str
    rounds: List[str]
    total_games: int
    processed_count: Optional[int] = None
    error_count: Optional[int] = None
    available_games: Optional[int] = None
    task_id: Optional[str] = None
    enrichment_status: Optional[str] = None
    enrichment_result: Optional[dict] = None
    message: str


class SeasonScrapeRequest(BaseModel):
    competition_id: str
    season_id: str


class RoundScrapeRequest(SeasonScrapeRequest):
    round: str


class AutonomousScrapeRequest(SeasonScrapeRequest):
    pass


def queue_scrape_task(
    db: Session,
    workflow: str,
    competition_id: str,
    season_id: str,
    round_name: Optional[str] = None,
) -> TaskTracker:
    tracker = TaskTracker(
        db,
        "SportsDynamics",
        workflow,
        competition_id,
        season_id,
        round_name=round_name,
    )
    return tracker


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/scrape-schedule")
async def initialize_season_endpoint(
    request: SeasonScrapeRequest,
    db: Session = Depends(get_db),
):
    """Initialize or refresh the season schedule, then synchronize teams."""
    try:
        tracker = queue_scrape_task(db, "season_initialization", request.competition_id, request.season_id)
        initialize_season_task.delay(tracker.id, request.competition_id, request.season_id)
        return {"status": "queued", "task_id": tracker.id, "workflow": "season_initialization"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Season initialization failed: {exc}")


@router.post("/scrape-unified")
async def scrape_round_endpoint(
    request: RoundScrapeRequest,
    db: Session = Depends(get_db),
):
    """Clear and process all available games from one round, then enrich players."""
    try:
        tracker = queue_scrape_task(db, "round_scrape", request.competition_id, request.season_id, request.round)
        scrape_round_task.delay(tracker.id, request.competition_id, request.season_id, request.round)
        return {"status": "queued", "task_id": tracker.id, "workflow": "round_scrape", "round": request.round}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Round scrape failed: {exc}")


@router.post("/scrape-autonome")
async def scrape_autonomous_endpoint(
    request: AutonomousScrapeRequest,
    db: Session = Depends(get_db),
):
    """Detect and process new or changed available games for a season."""
    try:
        tracker = queue_scrape_task(db, "autonomous_scrape", request.competition_id, request.season_id)
        scrape_autonomous_task.delay(tracker.id, request.competition_id, request.season_id)
        return {"status": "queued", "task_id": tracker.id, "workflow": "autonomous_scrape"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Autonomous scrape failed: {exc}")


@router.post("/scrape-autonome/dry-run")
async def scrape_autonomous_dry_run_endpoint(
    request: AutonomousScrapeRequest,
    db: Session = Depends(get_db),
):
    """Preview new or changed available games without modifying the database."""
    try:
        return autonomous_dry_run(db, request.competition_id, request.season_id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Autonomous dry-run failed: {exc}")

# Legacy route retained as an internal implementation; not exposed publicly.
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
            filters["season_name"] = ids_mapping['season_name']
        
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


# Legacy route retained as an internal implementation; not exposed publicly.
async def scrape_full_season(
    request: FullSeasonScrapeRequest,
    db: Session = Depends(get_db)
):
    """
    Scrape ALL games from a complete season in one request
    
    Automatically loops through all pages until all games are downloaded.
    
    **Request Body:**
    ```json
    {
        "league_name": "Ligue 1",
        "season_name": "2024 - 2025"
    }
    ```
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8001/games/full-season-scrape \
      -H "Content-Type: application/json" \
      -d '{
        "league_name": "Ligue 1",
        "season_name": "2024 - 2025"
      }'
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "league": "Ligue 1",
        "season": "2024 - 2025",
        "total_games": 380,
        "message": "✅ Downloaded 380 games successfully"
    }
    ```
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Map league and season names to IDs
        ids_mapping = get_sportsdynamics_ids(request.league_name, request.season_name)
        competition_id = ids_mapping["competitionId"]
        season_id = ids_mapping["seasonId"]
        
        logger.info(f"📊 Starting full season scrape:")
        logger.info(f"  - League: {request.league_name}")
        logger.info(f"  - Season: {request.season_name}")
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
            filters["season_name"] = request.season_name
        
        logger.info(f"🔍 Filters: {filters}")
        
        # Loop through all pages
        all_games = []
        page = 1
        limit = 380  # Max per page
        
        while True:
            logger.info(f"📄 Scraping page {page}...")
            
            try:
                games = await coordinator.scrape_games(
                    filters=filters,
                    limit=limit,
                    page=page
                )
                
                if not games:
                    logger.info(f"✅ No more games on page {page}, stopping")
                    break
                
                all_games.extend(games)
                logger.info(f"  ✓ Page {page}: {len(games)} games (total: {len(all_games)})")
                
                # Stop if we got less than limit (means we're on last page)
                if len(games) < limit:
                    logger.info(f"✅ Last page reached (only {len(games)} games)")
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"❌ Error on page {page}: {str(e)}")
                break
        
        logger.info(f"✅ Full season scrape completed: {len(all_games)} games total")
        
        return FullSeasonScrapeResponse(
            status="success",
            league=request.league_name,
            season=request.season_name or "All seasons",
            total_games=len(all_games),
            message=f"✅ Downloaded {len(all_games)} games successfully"
        )
        
    except ValueError as e:
        # Filter validation error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors
        logger.error(f"❌ Full season scrape failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Full season scrape failed: {str(e)}")


# Legacy route retained as an internal implementation; not exposed publicly.
async def scrape_schedule(
    request: FullSeasonScrapeRequest,
    db: Session = Depends(get_db)
):
    """
    Scrape ONLY the basic schedule/calendar information (NO JSON files)
    
    Perfect for season initialization. Downloads only:
    - Match date, time, teams, result
    - NO 4 JSON files (metadata, distance, fitness, rgd)
    - NO parsing of lineups/events/fitness data
    
    Much faster than full scrape (~30 seconds for 380 games vs 2-3 minutes).
    
    **Request Body:**
    ```json
    {
        "league_name": "Ligue 2",
        "season_name": "2024 - 2025"
    }
    ```
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/games/scrape-schedule \
      -H "Content-Type: application/json" \
      -d '{
        "league_name": "Ligue 2",
        "season_name": "2024 - 2025"
      }'
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "league": "Ligue 2",
        "season": "2024 - 2025",
        "total_games": 380,
        "message": "✅ Downloaded 380 games successfully (schedule only)"
    }
    ```
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Create task for tracking
    task_id = str(uuid.uuid4())
    task = ScrapingTask(
        id=task_id,
        provider="SportsDynamics",
        competition_id="",  # Will update after ID lookup
        season_id="",  # Will update after ID lookup
        status=TaskStatus.RUNNING,
        total_items=0,
        processed_items=0,
        failed_items=0,
        started_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    
    def log_task(level: str, message: str, item_id: str = None, item_name: str = None):
        """Helper to log messages to both logger and database"""
        logger.log(getattr(logging, level), message)
        log_entry = ScrapingLog(
            id=str(uuid.uuid4()),
            task_id=task_id,
            level=level,
            message=message,
            item_id=item_id,
            item_name=item_name,
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
    
    try:
        # Map league and season names to IDs
        ids_mapping = get_sportsdynamics_ids(request.league_name, request.season_name)
        competition_id = ids_mapping["competitionId"]
        season_id = ids_mapping["seasonId"]
        
        # Update task with IDs
        task.competition_id = competition_id
        task.season_id = season_id
        db.commit()
        
        log_task("INFO", f"📅 Starting schedule scrape (no files):", item_name=request.league_name)
        log_task("INFO", f"  - League: {request.league_name}")
        log_task("INFO", f"  - Season: {request.season_name}")
        log_task("INFO", f"  - Competition ID: {competition_id}")
        log_task("INFO", f"  - Season ID: {season_id}")
        
        # Initialize coordinator
        coordinator = ScraperCoordinator()
        
        # Build filter dictionary
        filters = {
            "available": True,
            "competition_id": competition_id,
        }
        
        if season_id:
            filters["season_id"] = season_id
            filters["season_name"] = request.season_name
        
        log_task("INFO", f"🔍 Filters configured")
        
        # Loop through all pages using BASIC scraping (no files)
        all_games = []
        page = 1
        limit = 380  # Max per page
        errors_count = 0
        
        while True:
            log_task("INFO", f"📄 Scraping page {page} (schedule only)...")
            
            try:
                games = await coordinator.scrape_games_basic(
                    filters=filters,
                    limit=limit,
                    page=page
                )
                
                if not games:
                    log_task("INFO", f"✅ No more games on page {page}, stopping")
                    break
                
                all_games.extend(games)
                log_task("INFO", f"  ✓ Page {page}: {len(games)} games (total: {len(all_games)})")
                
                # Update processed count
                task.processed_items = len(all_games)
                task.total_items = len(all_games) + (limit if len(games) == limit else 0)
                db.commit()
                
                # Stop if we got less than limit (means we're on last page)
                if len(games) < limit:
                    log_task("INFO", f"✅ Last page reached (only {len(games)} games)")
                    break
                
                page += 1
                
            except Exception as e:
                errors_count += 1
                task.failed_items = errors_count
                db.commit()
                log_task("ERROR", f"❌ Error on page {page}: {str(e)}")
                break
        
        log_task("INFO", f"✅ Schedule scrape completed: {len(all_games)} games total")
        
        # Update task status
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.total_items = len(all_games)
        task.processed_items = len(all_games)
        db.commit()
        
        return FullSeasonScrapeResponse(
            status="success",
            league=request.league_name,
            season=request.season_name or "All seasons",
            total_games=len(all_games),
            message=f"✅ Downloaded {len(all_games)} games successfully (schedule only, no files)"
        )
        
    except ValueError as e:
        # Filter validation error
        log_task("ERROR", f"❌ Validation error: {str(e)}")
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors
        log_task("ERROR", f"❌ Schedule scrape failed: {str(e)}")
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Schedule scrape failed: {str(e)}")


# Legacy route retained as an internal implementation; not exposed publicly.
async def scrape_weekly(
    request: FullSeasonScrapeRequest,
    db: Session = Depends(get_db)
):
    """
    Scrape available JSON files for games (WEEK/Weekly scrape)
    
    Downloads JSON files (metadata, distance_covered, fitness_entities) for all games
    that have files available.
    
    **Request Body:**
    ```json
    {
        "league_name": "Ligue 2",
        "season_name": "2024 - 2025"
    }
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "league": "Ligue 2",
        "season": "2024 - 2025",
        "total_games": 380,
        "available_games": 45,
        "processed_count": 42,
        "error_count": 3,
        "task_id": "uuid-here",
        "message": "Processed 42 available games (3 errors)"
    }
    ```
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/games/scrape-weekly \
      -H "Content-Type: application/json" \
      -d '{
        "league_name": "Ligue 2",
        "season_name": "2026 - 2027"
      }'
    ```
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Create task for tracking
    task_id = str(uuid.uuid4())
    task = ScrapingTask(
        id=task_id,
        provider="SportsDynamics",
        competition_id="",  # Will update after ID lookup
        season_id="",  # Will update after ID lookup
        status="pending",  # Will update to running
        total_items=0,
        processed_items=0,
        failed_items=0,
        started_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    
    def log_task(level: str, message: str, item_id: str = None, item_name: str = None):
        """Helper to log messages to both logger and database"""
        logger.log(getattr(logging, level), message)
        log_entry = ScrapingLog(
            id=str(uuid.uuid4()),
            task_id=task_id,
            level=level,
            message=message,
            item_id=item_id,
            item_name=item_name,
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
    
    try:
        # Update status to running
        task.status = "running"
        db.commit()
        
        # Map league and season names to IDs
        ids_mapping = get_sportsdynamics_ids(request.league_name, request.season_name)
        competition_id = ids_mapping["competitionId"]
        season_id = ids_mapping["seasonId"]
        
        # Update task with IDs
        task.competition_id = competition_id
        task.season_id = season_id
        db.commit()
        
        log_task("INFO", f"🌟 Starting weekly scrape (download available files):")
        log_task("INFO", f"  - League: {request.league_name}")
        log_task("INFO", f"  - Season: {request.season_name}")
        log_task("INFO", f"  - Competition ID: {competition_id}")
        log_task("INFO", f"  - Season ID: {season_id}")
        
        # Initialize coordinator
        coordinator = ScraperCoordinator()
        
        # Build filter dictionary
        filters = {
            "available": True,  # Only available games
            "competition_id": competition_id,
        }
        
        if season_id:
            filters["season_id"] = season_id
            filters["season_name"] = request.season_name
        
        round_names = request.round_names or []
        if request.round:
            round_names = [request.round]

        if round_names:
            filters["round"] = [str(round_name) for round_name in round_names]
            log_task("INFO", f"  - Round filters: {filters['round']}")
        
        log_task("INFO", f"🔍 Filters configured")
        
        # Scrape available files for a single page (all available games)
        result = await coordinator.scrape_available_files(
            filters=filters,
            limit=380,
            page=1
        )
        
        # Update task with results
        task.total_items = result.get("total_games", 0)
        task.processed_items = result.get("processed_count", 0)
        task.failed_items = result.get("error_count", 0)
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        
        log_task("INFO", f"✅ Weekly scrape completed:")
        log_task("INFO", f"  - Total games: {result.get('total_games')}")
        log_task("INFO", f"  - Available: {result.get('available_games')}")
        log_task("INFO", f"  - Processed: {result.get('processed_count')}")
        log_task("INFO", f"  - Errors: {result.get('error_count')}")
        
        return {
            "status": "success",
            "league": request.league_name,
            "season": request.season_name or "All seasons",
            "total_games": result.get("total_games"),
            "available_games": result.get("available_games"),
            "processed_count": result.get("processed_count"),
            "error_count": result.get("error_count"),
            "task_id": task_id,
            "message": result.get("message")
        }
        
    except ValueError as e:
        # Filter validation error
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        log_task("ERROR", f"❌ Filter validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        log_task("ERROR", f"❌ Weekly scrape failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Weekly scrape failed: {str(e)}")


# Legacy route retained as an internal implementation; not exposed publicly.
async def scrape_unified(
    request: UnifiedScrapeRequest,
    db: Session = Depends(get_db)
):
    """
    🎯 UNIFIED SCRAPE ENDPOINT - Customizable scraping with filters
    
    Single endpoint that combines /scrape, /scrape-schedule, and /scrape-weekly functionality.
    
    **Features:**
    - Multi-round selection
    - Toggle available files only
    - Auto-calculate limit based on rounds (limit = rounds * 10)
    - Auto-loop all pages
    - Two modes: schedule (basic) or weekly (with available files)
    
    **Request Body:**
    ```json
    {
        "league_name": "Ligue 2",
        "season_name": "2024 - 2025",
        "round_names": ["1", "2", "3"],
        "available_only": true,
        "mode": "weekly"
    }
    ```
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/games/scrape-unified \
      -H "Content-Type: application/json" \
      -d '{
        "league_name": "Ligue 2",
        "season_name": "2026 - 2027",
        "round_names": ["1", "2"],
        "available_only": true,
        "mode": "weekly"
      }'
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "league": "Ligue 2",
        "season": "2026 - 2027",
        "mode": "weekly",
        "rounds": ["1", "2"],
        "total_games": 20,
        "processed_count": 18,
        "error_count": 0,
        "available_games": 18,
        "task_id": "uuid-here",
        "message": "✅ Processed 18 available games from 2 rounds"
    }
    ```
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Create task for tracking
    task_id = str(uuid.uuid4())
    task = ScrapingTask(
        id=task_id,
        provider="SportsDynamics",
        competition_id="",
        season_id="",
        status=TaskStatus.RUNNING,
        total_items=0,
        processed_items=0,
        failed_items=0,
        started_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    
    # Accumulate logs to batch insert instead of commiting each time
    pending_logs = []
    
    def log_task(level: str, message: str, item_id: str = None, item_name: str = None):
        """Helper to log to logger and accumulate for batch insert"""
        logger.log(getattr(logging, level), message)
        # Accumulate logs but don't commit yet (avoid transaction rollback issues)
        log_entry = ScrapingLog(
            id=str(uuid.uuid4()),
            task_id=task_id,
            level=level,
            message=message,
            item_id=item_id,
            item_name=item_name,
            timestamp=datetime.utcnow()
        )
        pending_logs.append(log_entry)
    
    def flush_pending_logs():
        """Flush accumulated logs to database"""
        if pending_logs:
            for log_entry in pending_logs:
                db.add(log_entry)
            db.commit()
            pending_logs.clear()
    
    try:
        # Map league and season names to IDs
        ids_mapping = get_sportsdynamics_ids(request.league_name, request.season_name)
        competition_id = ids_mapping["competitionId"]
        season_id = ids_mapping["seasonId"]
        
        # Update task with IDs
        task.competition_id = competition_id
        task.season_id = season_id
        db.commit()
        
        # Normalize round_names
        round_names = request.round_names or []
        if isinstance(round_names, str):
            round_names = [round_names]
        round_names = [str(r) for r in round_names]  # Ensure strings
        
        log_task("INFO", f"🎯 Starting unified scrape:")
        log_task("INFO", f"  - League: {request.league_name}")
        log_task("INFO", f"  - Season: {request.season_name}")
        log_task("INFO", f"  - Rounds: {', '.join(round_names) if round_names else 'ALL'}")
        log_task("INFO", f"  - Mode: {request.mode}")
        log_task("INFO", f"  - Available only: {request.available_only}")
        log_task("INFO", f"  - Competition ID: {competition_id}")
        log_task("INFO", f"  - Season ID: {season_id}")
        
        # Calculate limit based on number of rounds
        limit = (len(round_names) if round_names else 1) * 10
        log_task("INFO", f"  - Auto-calculated limit: {limit}")
        
        # Initialize coordinator
        coordinator = ScraperCoordinator()
        
        # Build filter dictionary
        filters = {
            "competition_id": competition_id,
        }
        
        if request.available_only:
            filters["available"] = True
        
        if season_id:
            filters["season_id"] = season_id
            filters["season_name"] = request.season_name
        
        if round_names:
            filters["round"] = round_names
        
        log_task("INFO", f"Filters configured")
        
        # Scrape based on mode
        processed_count = 0
        error_count = 0
        available_games = 0
        total_games = 0
        enrichment_status = "skipped"
        enrichment_result = None
        
        try:
            if request.mode == "weekly":
                # Mode WEEKLY: Use scrape_available_files (one call, processes internally)
                log_task("INFO", f"Calling scrape_available_files (weekly mode with JSON files)...")
                result = await coordinator.scrape_available_files(
                    filters=filters,
                    limit=limit,
                    page=1
                )
                
                total_games = result.get("total_games", 0)
                available_games = result.get("available_games", 0)
                processed_count = result.get("processed_count", 0)
                error_count = result.get("error_count", 0)
                
                log_task("INFO", f"Weekly scrape result: processed={processed_count}, available={available_games}, errors={error_count}")
                
            else:  # SCHEDULE mode
                # Mode SCHEDULE: Use scrape_games_basic with pagination
                all_games = []
                page = 1
                
                while True:
                    log_task("INFO", f"Scraping page {page} (limit={limit}, schedule mode)...")
                    
                    games = await coordinator.scrape_games_basic(
                        filters=filters,
                        limit=limit,
                        page=page
                    )
                    
                    if not games:
                        log_task("INFO", f"No more games on page {page}, stopping")
                        break
                    
                    all_games.extend(games)
                    processed_count += len(games)
                    available_games += len(games)
                    
                    log_task("INFO", f"Page {page}: {len(games)} games loaded (total: {len(all_games)})")
                    
                    # Update task progress
                    task.processed_items = len(all_games)
                    task.total_items = len(all_games) + (limit if len(games) == limit else 0)
                    db.commit()
                    
                    # Stop if we got less than limit (last page)
                    if len(games) < limit:
                        log_task("INFO", f"Last page reached (only {len(games)} games)")
                        break
                    
                    page += 1
                
                total_games = len(all_games)
        
        except Exception as e:
            error_count += 1
            task.failed_items = error_count
            db.commit()
            log_task("ERROR", f"Scrape error: {str(e)}")
            raise

        # Enrich players once, after all requested rounds have been parsed and persisted.
        if processed_count > 0:
            try:
                from .players import enrich_players_for_games

                season = db.query(Season).filter(
                    Season.competition_id == competition_id,
                    Season.name == (request.season_name or "")
                ).first()
                if not season:
                    raise ValueError(
                        f"Persisted season not found for competition {competition_id}: "
                        f"{request.season_name or 'unknown'}"
                    )

                log_task("INFO", "Starting player enrichment for processed games")
                enrichment_result = await enrich_players_for_games(
                    db=db,
                    competition_id=competition_id,
                    season_id=season.id,
                )
                enrichment_status = enrichment_result.get("status", "unknown")
                if enrichment_status == "error":
                    error_count += 1
                    log_task("ERROR", "Player enrichment returned an error")
                else:
                    log_task(
                        "INFO",
                        "Player enrichment completed: "
                        f"created={enrichment_result.get('created', 0)}, "
                        f"updated={enrichment_result.get('updated', 0)}, "
                        f"skipped={enrichment_result.get('skipped', 0)}"
                    )
            except Exception as e:
                enrichment_status = "error"
                enrichment_result = {"status": "error", "message": str(e)}
                error_count += 1
                log_task("ERROR", f"Player enrichment failed: {str(e)}")
        else:
            log_task("INFO", "Player enrichment skipped: no games were processed")
        
        log_task("INFO", f"Unified scrape completed:")
        log_task("INFO", f"  - Mode: {request.mode}")
        log_task("INFO", f"  - Total games: {total_games}")
        log_task("INFO", f"  - Available: {available_games}")
        log_task("INFO", f"  - Processed: {processed_count}")
        log_task("INFO", f"  - Errors: {error_count}")
        
        # Update task status
        task.status = TaskStatus.COMPLETED if error_count == 0 else TaskStatus.FAILED
        task.completed_at = datetime.utcnow()
        task.total_items = total_games
        task.processed_items = processed_count
        task.failed_items = error_count
        if error_count > 0:
            task.error_message = "One or more cycle phases failed"
        db.commit()
        
        # Log details for each match (use fresh session to avoid transaction issues)
        try:
            from src.config.database import SessionLocal
            fresh_session = SessionLocal()
            
            # Convert season_id (SportsDynamics integer) to UUID if present
            season_uuid = None
            if season_id:
                from src.SportsDynamics.models.competition import Season
                season_obj = fresh_session.query(Season).filter(
                    Season.competition_id == competition_id,
                    Season.name == (request.season_name or "")
                ).first()
                if season_obj:
                    season_uuid = season_obj.id
            
            query = fresh_session.query(Game).filter(Game.competition_id == competition_id)
            if season_uuid:
                query = query.filter(Game.season_id == season_uuid)
            if round_names:
                query = query.filter(Game.round_name.in_(round_names))
            
            games_to_log = query.all()
            log_task("INFO", f"Games processed ({len(games_to_log)} total):")
            
            for game in games_to_log:
                # Use raw SQL for counting since table names don't match ORM models
                from sqlalchemy import text
                
                goals_count = fresh_session.execute(
                    text("SELECT COUNT(*) as cnt FROM goals WHERE game_id = :game_id"),
                    {"game_id": game.id}
                ).scalar() or 0
                
                cards_count = fresh_session.execute(
                    text("SELECT COUNT(*) as cnt FROM card WHERE game_id = :game_id"),
                    {"game_id": game.id}
                ).scalar() or 0
                
                lineups_count = fresh_session.execute(
                    text("""
                        SELECT COUNT(*) as cnt FROM lineup_players
                        WHERE lineup_team_id IN (
                            SELECT id FROM lineup_teams WHERE game_id = :game_id
                        )
                    """),
                    {"game_id": game.id}
                ).scalar() or 0
                
                log_task(
                    "INFO",
                    f"  {game.name}: 1 game | {goals_count} goals | {cards_count} cards | {lineups_count} lineups",
                    item_id=game.id,
                    item_name=game.name
                )
            
            fresh_session.close()
        except Exception as e:
            logger.warning(f"Could not log game details: {str(e)}")
        
        # Flush all accumulated logs
        flush_pending_logs()
        
        return UnifiedScrapeResponse(
            status="success" if error_count == 0 else "partial",
            league=request.league_name,
            season=request.season_name or "All seasons",
            mode=request.mode,
            rounds=round_names if round_names else ["ALL"],
            total_games=total_games,
            processed_count=processed_count,
            error_count=error_count,
            available_games=available_games,
            task_id=task_id,
            enrichment_status=enrichment_status,
            enrichment_result=enrichment_result,
            message=f"✅ Processed {processed_count} games from {len(round_names or ['ALL'])} round(s) in {request.mode} mode" + (f" ({error_count} errors)" if error_count > 0 else "")
        )
        
    except ValueError as e:
        # Filter validation error
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        log_task("ERROR", f"Filter validation error: {str(e)}")
        flush_pending_logs()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        log_task("ERROR", f"Unified scrape failed: {str(e)}")
        flush_pending_logs()
        raise HTTPException(status_code=500, detail=f"Unified scrape failed: {str(e)}")


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(task_id: str, db: Session = Depends(get_db)):
    """
    Get all logs for a scraping task
    
    **Example:**
    ```bash
    curl http://localhost:8001/games/tasks/66adc3e3-60d5-481d-99bf-43f06ea54e75/logs
    ```
    
    **Response:**
    ```json
    {
      "task_id": "66adc3e3-60d5-481d-99bf-43f06ea54e75",
      "total_logs": 12,
      "logs": [
        {
          "timestamp": "2026-08-27T11:22:35.123456",
          "level": "INFO",
          "message": "Nantes vs Red Star: 1 game | 0 goals | 0 cards | 0 lineups",
          "item_name": "Nantes vs Red Star"
        },
        ...
      ]
    }
    ```
    """
    logs = db.query(ScrapingLog).filter(
        ScrapingLog.task_id == task_id
    ).order_by(ScrapingLog.timestamp).all()
    
    if not logs:
        raise HTTPException(status_code=404, detail=f"No logs found for task {task_id}")
    
    return {
        "task_id": task_id,
        "total_logs": len(logs),
        "logs": [
            {
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level,
                "message": log.message,
                "item_id": log.item_id,
                "item_name": log.item_name,
                "round": log.round,
                "context": log.context,
                "stats": log.stats,
                "level": log.level
            }
            for log in logs
        ]
    }


@router.get("/tasks/{task_id}/game-stats")
async def get_task_game_stats(task_id: str, db: Session = Depends(get_db)):
    """
    Get game-level statistics for a scraping task
    
    Returns all games processed in a task with per-table DELETE/INSERT counts
    
    **Example:**
    ```bash
    curl http://localhost:8001/games/tasks/66adc3e3-60d5-481d-99bf-43f06ea54e75/game-stats
    ```
    
    **Response:**
    ```json
    {
      "task_id": "66adc3e3-60d5-481d-99bf-43f06ea54e75",
      "total_games": 9,
      "games": [
        {
          "game_id": "uuid",
          "game_name": "Nantes vs Nancy",
          "round": "1",
          "stats": {
            "game_goals": {"deleted": 5, "inserted": 8},
            "game_cards": {"deleted": 3, "inserted": 7},
            "events": {"deleted": 150, "inserted": 200},
            ...
          }
        }
      ]
    }
    ```
    """
    logs = db.query(ScrapingLog).filter(
        ScrapingLog.task_id == task_id
    ).all()
    
    if not logs:
        raise HTTPException(status_code=404, detail=f"No logs found for task {task_id}")
    
    # Group logs by game (item_id)
    games_dict = {}
    
    for log in logs:
        if log.item_id:  # Only process logs with item_id (game_id)
            if log.item_id not in games_dict:
                games_dict[log.item_id] = {
                    "game_id": log.item_id,
                    "game_name": log.item_name or "Unknown",
                    "round": log.round or "N/A",
                    "stats": {}
                }
            
            # Merge stats from this log
            if log.stats and isinstance(log.stats, dict):
                for table_name, counts in log.stats.items():
                    if table_name not in games_dict[log.item_id]["stats"]:
                        games_dict[log.item_id]["stats"][table_name] = {
                            "deleted": 0,
                            "inserted": 0
                        }
                    
                    # Aggregate counts
                    if isinstance(counts, dict):
                        games_dict[log.item_id]["stats"][table_name]["deleted"] += counts.get("deleted", 0)
                        games_dict[log.item_id]["stats"][table_name]["inserted"] += counts.get("inserted", 0)
    
    # Convert to list and sort by game_name
    games_list = sorted(games_dict.values(), key=lambda x: x["game_name"])
    
    return {
        "task_id": task_id,
        "total_games": len(games_list),
        "games": games_list
    }


@router.get("/tasks/list")
async def list_tasks(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List all scraping tasks with their summaries
    
    Returns last N tasks ordered by creation date (most recent first)
    
    **Response:**
    ```json
    {
      "total": 150,
      "limit": 50,
      "offset": 0,
      "tasks": [
        {
          "id": "uuid",
          "status": "completed",
          "created_at": "2026-09-08T10:30:00",
          "started_at": "2026-09-08T10:30:05",
          "completed_at": "2026-09-08T10:35:45",
          "total_items": 380,
          "processed_items": 380,
          "failed_items": 0,
          "progress_percent": 100,
          "log_count": 2847,
          "game_count": 12,
          "provider": "sportsdynamics"
        }
      ]
    }
    ```
    """
    try:
        reconcile_stale_tasks(db)
        # Get total count
        total = db.query(ScrapingTask).count()
        
        # Get tasks (most recent first)
        tasks = db.query(ScrapingTask).order_by(ScrapingTask.created_at.desc()).offset(offset).limit(limit).all()
        
        # Build response with log counts per task
        tasks_data = []
        for task in tasks:
            log_count = db.query(ScrapingLog).filter(ScrapingLog.task_id == task.id).count()
            game_count = db.query(ScrapingLog).filter(
                ScrapingLog.task_id == task.id,
                ScrapingLog.item_id.isnot(None)
            ).distinct(ScrapingLog.item_id).count()
            
            tasks_data.append({
                "id": task.id,
                "status": task.status,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "total_items": task.total_items,
                "processed_items": task.processed_items,
                "failed_items": task.failed_items,
                "cancel_requested": task.cancel_requested,
                "progress_percent": task.progress_percent,
                "log_count": log_count,
                "game_count": game_count,
                "provider": task.provider,
                "workflow": task.workflow,
                "competition_id": task.competition_id,
                "season_id": task.season_id,
                "round_name": task.round_name,
                "current_phase": task.current_phase,
                "current_item_id": task.current_item_id,
                "error_message": task.error_message,
                "extra_metadata": task.extra_metadata or {},
            })
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "tasks": tasks_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    """Request a running or pending task to stop at its next safe checkpoint."""
    task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
        raise HTTPException(status_code=409, detail="Only pending or running tasks can be cancelled")

    task.cancel_requested = True
    db.add(task)
    db.commit()
    return {"status": "cancellation_requested", "task_id": task.id}


# Legacy route retained as an internal implementation; not exposed publicly.
async def test_scrape():
    """
    Quick test endpoint - scrape a few games without filters
    
    **Usage:**
    ```bash
    curl -X GET http://localhost:8000/games/scrape/test
    ```
    """
    try:
        # Generate task_id for logging
        task_id = str(uuid.uuid4())
        
        coordinator = ScraperCoordinator(task_id=task_id)
        
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
            "task_id": task_id,
            "count": len(games),
            "games": games,
            "message": f"Test successful - got {len(games)} games. Check logs at /games/tasks/{task_id}/logs"
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

@router.get("/rounds")
def get_available_rounds(
    competition_id: str = Query(None),
    season_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get all available rounds/journées from the database
    
    Returns a sorted list of unique round names
    
    **Example:**
    ```bash
    curl -X GET http://localhost:8001/games/rounds
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "rounds": ["1", "2", "3", ..., "34"],
        "total": 34
    }
    ```
    """
    try:
        # Get distinct round_names, sorted numerically
        rounds_query = db.query(Game.round_name).distinct()
        if competition_id:
            rounds_query = rounds_query.filter(Game.competition_id == competition_id)
        if season_id:
            rounds_query = rounds_query.filter(Game.season_id == season_id)
        rounds = [r[0] for r in rounds_query.all() if r[0]]
        
        # Sort numerically
        rounds_sorted = sorted(rounds, key=lambda x: int(x) if x.isdigit() else float('inf'))
        
        return {
            "status": "success",
            "rounds": rounds_sorted,
            "total": len(rounds_sorted)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch rounds: {str(e)}")


@router.get("/stats/events-by-game")
def get_events_by_game(
    round_number: str = Query(None, description="Round/Journée number (e.g., '1', '2', '4')"),
    competition_id: str = Query(None),
    season_id: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get event count for each game in a specific round
    
    Returns the number of events per game grouped by round
    
    **Parameters:**
    - `round_number` (optional): Round number to filter by. If omitted, returns data for all rounds
    
    **Example:**
    ```bash
    # Events for round 4 only
    curl -X GET "http://localhost:8001/games/stats/events-by-game?round_number=4"
    
    # All rounds
    curl -X GET "http://localhost:8001/games/stats/events-by-game"
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "round": "4",
        "games": [
            {
                "game_id": "uuid-1",
                "game_name": "Annecy vs Metz",
                "events_count": 2500,
                "lineups_count": 38
            },
            ...
        ],
        "total_games": 9,
        "total_events": 22245,
        "avg_events_per_game": 2471.67
    }
    ```
    """
    from sqlalchemy import func
    from src.SportsDynamics.models.events_hybrid_schema import Events
    
    try:
        query = db.query(
            Game.id,
            Game.name,
            Game.round_name,
            func.count(Events.id).label('events_count')
        ).outerjoin(Events).group_by(Game.id, Game.name, Game.round_name)
        
        if round_number:
            query = query.filter(Game.round_name == round_number)
        if competition_id:
            query = query.filter(Game.competition_id == competition_id)
        if season_id:
            query = query.filter(Game.season_id == season_id)
        
        query = query.order_by(
            cast(Game.round_name, Integer).nullslast(),
            Game.name
        )
        
        results = query.all()
        
        if not results:
            return {
                "status": "success",
                "round": round_number or "all",
                "games": [],
                "total_games": 0,
                "total_events": 0,
                "avg_events_per_game": 0
            }
        
        # Format results
        games_data = [
            {
                "game_id": r[0],
                "game_name": r[1],
                "events_count": r[3] or 0
            }
            for r in results
        ]
        
        total_events = sum(g["events_count"] for g in games_data)
        total_games = len(games_data)
        avg_events = total_events / total_games if total_games > 0 else 0
        
        return {
            "status": "success",
            "round": round_number or "all",
            "games": games_data,
            "total_games": total_games,
            "total_events": total_events,
            "avg_events_per_game": round(avg_events, 2)
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching events stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch events stats: {str(e)}")


@router.get("", response_model=list)
def list_games(
    competition_id: str = Query(None),
    season_id: str = Query(None),
    round_name: str = Query(None),
    team_id: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List games from database with optional filtering"""
    query = db.query(Game)
    
    if competition_id:
        query = query.filter(Game.competition_id == competition_id)
    if season_id:
        query = query.filter(Game.season_id == season_id)
    if round_name:
        query = query.filter(Game.round_name == round_name)
    if team_id:
        query = query.filter(
            (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
        )
    
    # Sort by round_name (numeric) then by starts_at
    query = query.order_by(
        cast(Game.round_name, Integer).nullslast(),
        Game.starts_at
    )
    
    games = query.offset(skip).limit(limit).all()
    
    # Convert ORM objects to dictionaries
    result = []
    for game in games:
        # Get game status (backref returns a list, get first if exists)
        status = game.status[0] if game.status and len(game.status) > 0 else None
        
        # Include team data (home_team and away_team with brand/logo)
        home_team = {
            'id': game.home_team.id if game.home_team else None,
            'name': game.home_team.name if game.home_team else None,
            'brand': game.home_team.brand if game.home_team else None,
            'logo_url': game.home_team.logo_url if game.home_team else None,
        } if game.home_team else {'id': None, 'name': None, 'brand': None}
        
        away_team = {
            'id': game.away_team.id if game.away_team else None,
            'name': game.away_team.name if game.away_team else None,
            'brand': game.away_team.brand if game.away_team else None,
            'logo_url': game.away_team.logo_url if game.away_team else None,
        } if game.away_team else {'id': None, 'name': None, 'brand': None}
        
        game_dict = {
            'id': game.id,
            'name': game.name,
            'home_score': game.home_score,
            'away_score': game.away_score,
            'round_name': game.round_name,
            'starts_at': game.starts_at.isoformat() if game.starts_at else None,
            'competition_id': game.competition_id,
            'season_id': game.season_id,
            'competition_name': game.competition.name if game.competition else None,
            'season_name': game.season.name if game.season else None,
            'data_processed': game.data_processed,
            'created_at': game.created_at.isoformat() if game.created_at else None,
            'updated_at': game.updated_at.isoformat() if game.updated_at else None,
            'home_team': home_team,
            'away_team': away_team,
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
            ] if game.output_files else [],
            'status': {
                'available': status.available if status else None,
                'is_ugd_available': status.is_ugd_available if status else None,
                'rgd_status': status.rgd_status if status else None,
                'ugd_status': status.ugd_status if status else None,
                'last_checked_at': status.last_checked_at.isoformat() if status and status.last_checked_at else None,
                'status_changed_at': status.status_changed_at.isoformat() if status and status.status_changed_at else None,
            } if status else None
        }
        result.append(game_dict)
    
    return result


@router.get("/{game_id}/download-json")
def download_game_json(game_id: str, db: Session = Depends(get_db)):
    """Download fresh SportsDynamics JSON files as an in-memory ZIP."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # URLs stored in OutputFile are intentionally ignored because they expire.
    coordinator = ScraperCoordinator()
    try:
        output_files = coordinator.provider.get_game_output_files(game_id).get("items", [])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not refresh SportsDynamics files: {exc}")
    finally:
        coordinator.close()

    archive = BytesIO()
    downloaded = 0
    try:
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zip_file:
            for file_item in output_files:
                if file_item.get("fileType") != "JSON":
                    continue
                file_info = file_item.get("file") or {}
                url = file_info.get("url")
                file_name = file_item.get("fileName") or f"file_{file_item.get('id', downloaded)}.json"
                if not url:
                    continue
                try:
                    with urlopen(url, timeout=30) as response:
                        zip_file.writestr(file_name, response.read())
                    downloaded += 1
                except (HTTPError, URLError) as exc:
                    logger.warning("Unable to download %s for game %s: %s", file_name, game_id, exc)
                    continue
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not build JSON archive: {exc}")

    if downloaded == 0:
        raise HTTPException(status_code=404, detail="No downloadable JSON files are currently available")

    archive.seek(0)
    safe_name = "_".join((game.name or game_id).split())
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.zip"'},
    )


@router.get("/{game_id}")
def get_game(game_id: str, db: Session = Depends(get_db)):
    """Get game by ID from database with lineups and status"""
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
                        'starting': lp.starting,
                        'position_name': lp.position,
                        'shirt_number': lp.shirt_number
                    }
                    for lp in lineup_team.lineup_players
                ] if lineup_team.lineup_players else []
            }
            lineups.append(team_lineup)
    
    # Get game status (backref returns a list, get first if exists)
    status = game.status[0] if game.status and len(game.status) > 0 else None
    
    # Convert ORM object to dictionary
    game_dict = {
        'id': game.id,
        'name': game.name,
        'home_score': game.home_score,
        'away_score': game.away_score,
        'round_name': game.round_name,
        'starts_at': game.starts_at.isoformat() if game.starts_at else None,
        'data_processed': game.data_processed,
        'created_at': game.created_at.isoformat() if game.created_at else None,
        'updated_at': game.updated_at.isoformat() if game.updated_at else None,
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
        ] if game.output_files else [],
        'status': {
            'available': status.available if status else None,
            'is_ugd_available': status.is_ugd_available if status else None,
            'rgd_status': status.rgd_status if status else None,
            'ugd_status': status.ugd_status if status else None,
            'last_checked_at': status.last_checked_at.isoformat() if status and status.last_checked_at else None,
            'status_changed_at': status.status_changed_at.isoformat() if status and status.status_changed_at else None,
            'created_at': status.created_at.isoformat() if status and status.created_at else None,
            'updated_at': status.updated_at.isoformat() if status and status.updated_at else None,
        } if status else None
    }
    
    return game_dict


@router.get("/{game_id}/raw-stats")
def get_game_raw_stats(game_id: str, db: Session = Depends(get_db)):
    """Return raw row counts for every match-specific data table."""
    from src.SportsDynamics.models import (
        GameStatus, OutputFile, Period, GameScoreEvolution, LineupTeam,
        LineupPlayer, GameSubstitution, TeamDistanceCovered,
        PlayerDistanceCovered, PlayerFitnessRun, PlayerFitnessSummary,
        TeamFitnessSummary, Events, Setpieces, IndividualPossession,
        PossessionCollective,
    )

    if not db.query(Game).filter(Game.id == game_id).first():
        raise HTTPException(status_code=404, detail="Game not found")

    counts = {
        "game_status": db.query(GameStatus).filter(GameStatus.game_id == game_id).count(),
        "output_files": db.query(OutputFile).filter(OutputFile.game_id == game_id).count(),
        "events": db.query(Events).filter(Events.game_id == game_id).count(),
        "periods": db.query(Period).filter(Period.game_id == game_id).count(),
        "game_score_evolution": db.query(GameScoreEvolution).filter(GameScoreEvolution.game_id == game_id).count(),
        "lineup_team": db.query(LineupTeam).filter(LineupTeam.game_id == game_id).count(),
        "lineup_player": db.query(LineupPlayer).join(LineupTeam).filter(LineupTeam.game_id == game_id).count(),
        "game_substitution": db.query(GameSubstitution).filter(GameSubstitution.game_id == game_id).count(),
        "team_distance_covered": db.query(TeamDistanceCovered).filter(TeamDistanceCovered.game_id == game_id).count(),
        "player_distance_covered": db.query(PlayerDistanceCovered).filter(PlayerDistanceCovered.game_id == game_id).count(),
        "player_fitness_runs": db.query(PlayerFitnessRun).filter(PlayerFitnessRun.game_id == game_id).count(),
        "player_fitness_summary": db.query(PlayerFitnessSummary).filter(PlayerFitnessSummary.game_id == game_id).count(),
        "team_fitness_summary": db.query(TeamFitnessSummary).filter(TeamFitnessSummary.game_id == game_id).count(),
        "setpieces": db.query(Setpieces).filter(Setpieces.game_id == game_id).count(),
        "individual_possession": db.query(IndividualPossession).filter(IndividualPossession.game_id == game_id).count(),
        "possession_collective": db.query(PossessionCollective).filter(PossessionCollective.game_id == game_id).count(),
    }
    return {"game_id": game_id, "tables": counts, "total_rows": sum(counts.values())}


@router.post("/{game_id}/scrape-game")
async def scrape_game_endpoint(
    game_id: str,
    db: Session = Depends(get_db),
):
    """Clear and process one available game, then enrich its players."""
    try:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        tracker = queue_scrape_task(db, "game_scrape", game.competition_id, game.season_id, game.round_name)
        scrape_game_task.delay(tracker.id, game_id)
        return {"status": "queued", "task_id": tracker.id, "workflow": "game_scrape", "game_id": game_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Game scrape failed: {exc}")


# Legacy route retained as an internal implementation; not exposed publicly.
async def force_scrape_game(game_id: str, db: Session = Depends(get_db)):
    """
    Force rescrape a specific game from SportsDynamics API
    Deletes all related data (periods, squads, lineups, output_files) but keeps the Game record
    Then re-scrapes ONLY this specific game from the round (other games in round are NOT updated)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Generate task_id for logging
    task_id = str(uuid.uuid4())
    logger.info(f"🆔 Task ID: {task_id}")
    
    try:
        round_name = game.round_name
        competition_id = game.competition_id
        season_id = game.season_id
        
        # 1️⃣ Delete all related data
        logger.info(f"Clearing data for game {game_id}...")
        
        # Delete output files
        if game.output_files:
            for output_file in game.output_files:
                db.delete(output_file)
        
        # Delete lineups
        if game.lineups:
            for lineup in game.lineups:
                if lineup.lineup_players:
                    for lp in lineup.lineup_players:
                        db.delete(lp)
                db.delete(lineup)
        
        # Delete periods
        if game.periods:
            for period in game.periods:
                db.delete(period)
        
        db.commit()
        logger.info(f"✅ Data cleared for game {game_id}")
        
        # 2️⃣ Re-scrape the round with game_id_filter to persist ONLY this game
        logger.info(f"🔄 Re-scraping round {round_name} (persisting only {game_id})...")
        
        coordinator = ScraperCoordinator(task_id=task_id)
        filters = {
            "available": True,
            "competition_id": competition_id,
            "season_id": season_id,
            "round": [round_name]
        }
        
        # Scrape entire round but persist ONLY the target game
        scraped_games = await coordinator.scrape_games(
            filters=filters,
            limit=100,
            page=1,
            game_id_filter=game_id  # ✨ Only persist this game
        )
        
        if scraped_games and scraped_games[0].get("id") == game_id:
            logger.info(f"✅ Game {game_id} successfully re-scraped with fresh data")
            return {
                "status": "success",
                "message": f"✅ {game.name} successfully re-scraped with fresh data",
                "game_id": game.id,
                "game_name": game.name,
                "round_name": round_name
            }
        else:
            return {
                "status": "success",
                "message": f"✅ Data cleared and re-scrape initiated for {game.name} in round {round_name}",
                "game_id": game.id,
                "game_name": game.name,
                "round_name": round_name
            }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error force-scraping game {game_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error clearing game data: {str(e)}"
        )


# Legacy route retained as an internal implementation; not exposed publicly.
async def scrape_clubs(db: Session = Depends(get_db)):
    """
    Scrape clubs from SportsDynamics API and update team names in database
    
    **Purpose:**
    - Fetches all clubs from SportsDynamics
    - Updates team names in the database with real club information
    - Returns updated club information
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8001/games/clubs/scrape
    ```
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📡 Starting clubs scrape...")
        
        # Fetch clubs from API
        provider = ScraperCoordinator().provider
        clubs = provider.fetch_clubs()
        logger.info(f"✅ Fetched {len(clubs)} clubs from SportsDynamics")
        
        # Update teams in database
        updated_count = 0
        clubs_response = []
        
        for club in clubs:
            club_id = club.get("id")
            club_brand = club.get("brand")
            club_logo = club.get("logoUrl")
            club_providers = club.get("providers", {}).get("items", [])
            
            # Find existing team
            existing_team = db.query(Team).filter(Team.id == club_id).first()
            
            if existing_team:
                # Update with real name
                existing_team.name = club_brand or f"Team {club_id}"
                existing_team.brand = club_logo
                existing_team.providers = club_providers
                logger.info(f"  ✏️ Updated: {club_brand}")
                updated_count += 1
            else:
                # Create new team
                new_team = Team(
                    id=club_id,
                    name=club_brand or f"Team {club_id}",
                    brand=club_logo,
                    providers=club_providers
                )
                db.add(new_team)
                logger.info(f"  ➕ Created: {club_brand}")
                updated_count += 1
            
            clubs_response.append({
                "id": club_id,
                "name": club_brand,
                "logo_url": club_logo,
                "providers": club_providers
            })
        
        # Commit changes
        db.commit()
        logger.info(f"✅ Successfully updated {updated_count} teams")
        
        return ClubsScrapeResponse(
            status="success",
            count=len(clubs),
            updated=updated_count,
            clubs=clubs_response,
            message=f"Successfully scraped {len(clubs)} clubs and updated {updated_count} teams"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error scraping clubs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error scraping clubs: {str(e)}")
