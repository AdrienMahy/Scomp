"""SportsDynamics Provider - wraps the API client with business logic"""
from typing import Dict, Any, List, Optional
import logging

from src.SportsDynamics.api.client import SportsDynamicsClient
from src.config.filter_config import QueryFilterConfig

logger = logging.getLogger(__name__)


class SportsDynamicsProvider:
    """
    Wraps SportsDynamicsClient with business logic
    
    Responsibilities:
    - Validate filters
    - Transform simple filter values to GraphQL payloads
    - Handle caching (if needed)
    - Add business logic on top of raw API
    """
    
    def __init__(self):
        self.client = SportsDynamicsClient()
        self.filter_config = QueryFilterConfig()
    
    def fetch_games(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch games from SportsDynamics API
        
        Args:
            filters: Dict with filter values
                {
                    "competition_id": "comp-123",
                    "season_id": "season-456",
                    "round": ["Round 1", "Round 2"],
                    "available": True
                }
            limit: Number of results per page
            page: Page number
            
        Returns:
            List of game dictionaries with full details
            
        Raises:
            ValueError: If filters are invalid
            requests.RequestException: If API call fails
        """
        logger.info(f"Fetching games with filters: {filters}")

        try:
            limit = int(limit)
            page = int(page)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Pagination values must be integers: limit={limit!r}, page={page!r}") from exc
        if limit < 1 or page < 1:
            raise ValueError(f"Pagination values must be positive: limit={limit}, page={page}")
        
        # 1️⃣ Validate filters
        try:
            self.filter_config.validate_required_filters("get_games", filters)
        except ValueError as e:
            logger.error(f"Filter validation failed: {e}")
            raise
        
        logger.info(f"✅ Filters validated successfully")
        
        # 2️⃣ Extract competition_id (required)
        competition_id = filters.get("competition_id")
        if not competition_id:
            raise ValueError("competition_id is required")
        
        season_id = filters.get("season_id")
        round_names = filters.get("round")
        available = filters.get("available")  # Extract available filter
        
        logger.info(f"🎯 Extracted parameters:")
        logger.info(f"  - competition_id: {competition_id}")
        logger.info(f"  - season_id: {season_id}")
        logger.info(f"  - round_names: {round_names}")
        logger.info(f"  - available: {available}")
        
        # 3️⃣ Call API client
        try:
            logger.info(f"📡 Calling SportsDynamics API...")
            games = self.client.get_games(
                competition_id=competition_id,
                season_id=season_id,
                game_days=round_names,
                available=available,  # Pass available filter to client
                limit=limit,
                page=page
            )
            
            logger.info(f"✅ Successfully fetched {len(games)} games")
            
            # Log raw game structure (first game only for clarity)
            if games:
                import json
                logger.info(f"📦 Raw API Response (first game):\n{json.dumps(games[0], indent=2, default=str)}")
            
            return games
            
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise
    
    def get_game_output_files(self, game_id: str, limit: int = 30) -> Dict[str, Any]:
        """
        Get outputFiles for a specific game via separate API call
        This is needed because the main API doesn't return outputFiles for games with status=unchanged
        
        Args:
            game_id: Game ID
            limit: Max number of output files to return
            
        Returns:
            Dict with 'items' array of output files
        """
        logger.info(f"🔍 Getting output files for game {game_id}")
        try:
            output_files = self.client.get_game_output_files(game_id, limit)
            items_count = len(output_files.get("items", []))
            logger.info(f"✅ Got {items_count} output files for game {game_id}")
            return output_files
        except Exception as e:
            logger.error(f"❌ Failed to get output files for game {game_id}: {e}")
            raise
    
    def fetch_competitions(self) -> List[Dict[str, Any]]:
        """Fetch all competitions"""
        logger.info("Fetching competitions")
        return self.client.get_competitions()
    
    def fetch_seasons(self, competition_id: str) -> List[Dict[str, Any]]:
        """Fetch seasons for a competition"""
        logger.info(f"Fetching seasons for competition {competition_id}")
        return self.client.get_seasons(competition_id)
    
    def fetch_clubs(self) -> List[Dict[str, Any]]:
        """Fetch all clubs"""
        logger.info("Fetching clubs")
        return self.client.get_clubs()
    
    def fetch_players(self, limit: int = 500, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch all players with their profiles"""
        logger.info(f"Fetching players (limit={limit}, page={page})")
        return self.client.get_players(limit=limit, page=page)
