"""SportsDynamics API Client"""
import requests
from typing import Dict, Any, Optional, List

from ..config.settings import settings


class SportsDynamicsClient:
    """Client for SportsDynamics API"""
    
    def __init__(self, api_key: str = None, api_url: str = None):
        """
        Initialize SportsDynamics client
        
        Args:
            api_key: API key (defaults to settings)
            api_url: API URL (defaults to settings)
        """
        self.api_key = api_key or settings.sportsdynamics.api_key
        self.api_url = api_url or settings.sportsdynamics.api_url
        self.headers = {
            "x-sd-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute GraphQL query
        
        Args:
            query: GraphQL query string
            variables: Query variables dict
            
        Returns:
            Response data dict
            
        Raises:
            requests.RequestException: If API call fails
        """
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        import logging
        import json
        logger = logging.getLogger(__name__)
        
        # 📋 Print query and variables at INFO level for visibility
        logger.info(f"\n{'='*80}")
        logger.info(f"📋 GraphQL QUERY:")
        logger.info(f"{'='*80}")
        logger.info(query)
        logger.info(f"\n{'='*80}")
        logger.info(f"📝 VARIABLES:")
        logger.info(f"{'='*80}")
        logger.info(json.dumps(variables or {}, indent=2))
        logger.info(f"{'='*80}\n")
        
        logger.info(f"🚀 Calling SportsDynamics API at {self.api_url}...")
        
        response = requests.post(
            self.api_url,
            json=payload,
            headers=self.headers,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"✅ API response: 200 OK")
        else:
            logger.error(f"❌ API error: {response.status_code}")
            try:
                logger.error(json.dumps(response.json(), indent=2))
            except:
                logger.error(response.text[:500])
        
        response.raise_for_status()
        
        data = response.json()
        
        # Check for GraphQL errors
        if "errors" in data:
            raise ValueError(f"GraphQL error: {data['errors']}")
        
        return data.get("data", {})
    
    def get_games(self, 
                  competition_id: str,
                  season_id: str = None,
                  game_days: List[str] = None,
                  limit: int = 380,
                  page: int = 1) -> List[Dict[str, Any]]:
        """Get games for a competition/season"""
        query = """
        query getGames(
            $filters: [GameFilter!]
            $pagination: PaginationInput
            $sort: [GameSortPaginationInput!]
            ) {
            getGames(filters: $filters, pagination: $pagination, sort: $sort) {
                items {
                    id
                    name
                    result
                    startsAt
                    playedAt
                    available
                    isUGDAvailable
                    rgdStatus
                    ugdStatus
                    round { name }
                    homeScore
                    awayScore
                    homeTeamFormation
                    awayTeamFormation
                    homeTeam { brand id }
                    awayTeam { brand id }
                    outputFiles { items { id fileName fileType version isOutdated file { name size url } } }
                    squads { teamId players { items { id isStarting isCaptain jerseyNumber player { id firstName lastName } } } }
                    providers { items { id externalId provider { id name } } }
                }
            }
        }
        """
        #  periods { id periodId periodStartTime periodEndTime }

        filters = [{"available": {"equals": True}}]
        filters[0]["competition"] = {"id": {"equals": competition_id}}
        
        if season_id:
            # Season filter: {'season': {'equals': [year, year+1]}} with integers
            season_years = [int(season_id), int(season_id) + 1]
            filters[0]["season"] = {"season": {"equals": season_years}}
        
        if game_days:
            # Round filter: {'name': {'in': [list of round numbers as strings]}}
            filters[0]["round"] = {"name": {"in": game_days}}
        
        variables = {
            "filters": filters,
            "pagination": {"limit": limit, "page": page}
        }
        
        result = self.query(query, variables)
        return result.get("getGames", {}).get("items", [])
    
    def get_competitions(self) -> List[Dict[str, Any]]:
        """Get all competitions"""
        query = """
        query getCompetitions($pagination: PaginationInput) {
            getCompetitions(pagination: $pagination) {
                meta { count pageCount currentPage }
                items {
                    id
                    name
                    seasons { items { id name season } }
                }
            }
        }
        """
        
        variables = {"pagination": {"limit": 100, "page": 1}}
        result = self.query(query, variables)
        return result.get("getCompetitions", {}).get("items", [])
    
    def get_seasons(self, competition_id: str) -> List[Dict[str, Any]]:
        """Get seasons for a competition"""
        query = """
        query getSeasons($filters: [SeasonFilter!], $pagination: PaginationInput) {
            getSeasons(filters: $filters, pagination: $pagination) {
                meta { count pageCount currentPage }
                items {
                    id
                    name
                    season
                    stages { items { id name type } }
                }
            }
        }
        """
        
        filters = [{"competition": {"id": {"equals": competition_id}}}]
        variables = {
            "filters": filters,
            "pagination": {"limit": 100, "page": 1}
        }
        
        result = self.query(query, variables)
        return result.get("getSeasons", {}).get("items", [])
    
    def get_clubs(self) -> List[Dict[str, Any]]:
        """Get all clubs"""
        query = """
        query getClubs($pagination: PaginationInput) {
            getClubs(pagination: $pagination) {
                meta { count pageCount currentPage }
                items {
                    id
                    brand
                    logoUrl
                    providers { items { externalId provider { name } } }
                }
            }
        }
        """
        
        variables = {"pagination": {"limit": 100, "page": 1}}
        result = self.query(query, variables)
        return result.get("getClubs", {}).get("items", [])
