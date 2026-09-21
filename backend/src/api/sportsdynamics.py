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

        # Use debug logging for query and variables to avoid noisy stdout
        logger.debug("GraphQL query:\n%s", query)
        logger.debug("GraphQL variables: %s", json.dumps(variables or {}, indent=2))
        logger.info("Calling SportsDynamics API at %s", self.api_url)
        
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
                  available: bool = None,
                  limit: int = 100,
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
                    outputFiles(pagination: { limit: 30 }) { items { id fileName fileType version isOutdated file { name size url }  } } 
                    squads { teamId players { items { id isStarting isCaptain jerseyNumber player { id firstName lastName } } } }
                    providers { items { id externalId provider { id name } } }
                }
            }
        }
        """
        #  periods { id periodId periodStartTime periodEndTime }

        filters = [{}]
        filters[0]["competition"] = {"id": {"equals": competition_id}}
        
        # Add available filter if specified
        if available is not None:
            filters[0]["available"] = {"equals": available}
        
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
    
    def get_game_output_files(self, game_id: str, limit: int = 30) -> Dict[str, Any]:
        """
        Get outputFiles for a specific game
        This is a separate query because API may not return outputFiles for games with status=unchanged
        
        Args:
            game_id: Game ID
            limit: Max number of output files to return
            
        Returns:
            Dict with 'items' array of output files
        """
        query = """
        query getGame($filters: [GameFilter!]) {
            getGames(filters: $filters) {
                items {
                    id
                    outputFiles(pagination: { limit: %d }) {
                        items {
                            id
                            fileName
                            fileType
                            version
                            isOutdated
                            file {
                                name
                                size
                                url
                            }
                        }
                    }
                }
            }
        }
        """ % limit
        
        filters = [{"id": {"equals": game_id}}]
        variables = {"filters": filters}
        
        result = self.query(query, variables)
        games = result.get("getGames", {}).get("items", [])
        
        if games:
            return games[0].get("outputFiles", {"items": []})
        return {"items": []}
    
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
    
    def get_clubs(self, limit: int = 500, page: int = 1) -> List[Dict[str, Any]]:
        """
        Get all clubs with pagination
        
        Args:
            limit: Number of clubs per page (default: 500)
            page: Page number (default: 1)
            
        Returns:
            List of club dictionaries
        """
        query = """
        query getClubs($pagination: PaginationInput) {
            getClubs(pagination: $pagination) {
                meta { count pageCount currentPage }
                items {
                    id
                    name
                    brand
                    logoUrl
                    providers { items { externalId provider { name } } }
                }
            }
        }
        """
        
        variables = {"pagination": {"limit": limit, "page": page}}
        result = self.query(query, variables)
        return result.get("getClubs", {}).get("items", [])
    
    def get_clubs_by_ids(self, club_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple clubs by IDs in a SINGLE batch query using GraphQL aliases
        
        Args:
            club_ids: List of club IDs (can be large, API will batch automatically)
            
        Returns:
            List of club dictionaries
        """
        if not club_ids:
            return []
        
        # Build GraphQL query with aliases: club_0, club_1, club_2, etc.
        club_fields = """
            id
            name
            brand
            logoUrl
            providers {
                items {
                    externalId
                    provider {
                        name
                    }
                }
            }
        """
        
        # Build query with aliases (club_0, club_1, etc.)
        var_declarations = []
        var_definitions = {}
        query_aliases = []
        
        for idx, club_id in enumerate(club_ids):
            var_name = f"id{idx}"
            var_declarations.append(f"${var_name}: ID!")
            var_definitions[var_name] = club_id
            query_aliases.append(f'club_{idx}: getClubById(id: ${var_name}) {{ {club_fields} }}')
        
        query_string = f"""
        query getClubsByIds({', '.join(var_declarations)}) {{
            {' '.join(query_aliases)}
        }}
        """
        
        result = self.query(query_string, var_definitions)
        
        # Extract all club_X results and flatten into single list
        clubs = []
        for idx in range(len(club_ids)):
            club_data = result.get(f"club_{idx}")
            if club_data:
                clubs.append(club_data)
        
        return clubs
    
    
    def get_players(self, limit: int = 500, page: int = 1) -> List[Dict[str, Any]]:
        """
        Get all players with their details
        
        Args:
            limit: Number of players per page (default: 500)
            page: Page number (default: 1)
            
        Returns:
            List of player dictionaries
        """
        query = """
        query getPlayers($pagination: PaginationInput, $filters: [PlayerFilter!]) {
            getPlayers(pagination: $pagination, filters: $filters) {
                meta { count pageCount currentPage }
                items {
                    id
                    firstName
                    lastName
                    name
                    usageName
                    photo
                    age
                    birthdate
                    currentTeam {
                        id
                        brand
                    }
                    nationalities {
                        items {
                            id
                            country {
                                iso3
                            }
                            sportive
                        }
                    }
                    currentNationalTeam {
                        id
                        brand
                    }
                    positions {
                        items {
                            id
                            position {
                                name
                                code
                                group
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "pagination": {"limit": limit, "page": page}
        }
        
        result = self.query(query, variables)
        return result.get("getPlayers", {}).get("items", [])

    def get_player_by_id(self, player_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single player by ID with complete details
        
        Args:
            player_id: Player ID
            
        Returns:
            Player dictionary or None if not found
        """
        query = """
        query getPlayerById($id: ID!) {
            getPlayerById(id: $id) {
                id
                firstName
                lastName
                name
                usageName
                photo
                age
                birthdate
                currentTeam {
                    id
                    brand
                }
                nationalities {
                    items {
                        id
                        country {
                            iso3
                        }
                        sportive
                    }
                }
                currentNationalTeam {
                    id
                    brand
                }
                positions {
                    items {
                        id
                        position {
                            name
                            code
                            group
                        }
                    }
                }
            }
        }
        """
        
        variables = {"id": player_id}
        
        result = self.query(query, variables)
        return result.get("getPlayerById", None)

    def get_players_by_ids(self, player_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple players by IDs in a SINGLE batch query using GraphQL aliases
        
        Args:
            player_ids: List of player IDs (can be large, API will batch automatically)
            
        Returns:
            List of player dictionaries
        """
        if not player_ids:
            return []
        
        # Build GraphQL query with aliases: player_0, player_1, player_2, etc.
        player_fields = """
            id
            firstName
            lastName
            name
            usageName
            photo
            age
            birthdate
            currentTeam {
                id
                brand
            }
            nationalities {
                items {
                    id
                    country {
                        iso3
                    }
                    sportive
                }
            }
            currentNationalTeam {
                id
                brand
            }
            positions {
                items {
                    id
                    position {
                        name
                        code
                        group
                    }
                }
            }
        """
        
        # Build query with aliases (player_0, player_1, etc.)
        query_parts = ["query getPlayersByIds("]
        var_declarations = []
        var_definitions = {}
        query_aliases = []
        
        for idx, player_id in enumerate(player_ids):
            var_name = f"id{idx}"
            var_declarations.append(f"${var_name}: ID!")
            var_definitions[var_name] = player_id
            query_aliases.append(f'player_{idx}: getPlayerById(id: ${var_name}) {{ {player_fields} }}')
        
        query_string = f"""
        query getPlayersByIds({', '.join(var_declarations)}) {{
            {' '.join(query_aliases)}
        }}
        """
        
        result = self.query(query_string, var_definitions)
        
        # Extract all player_X results and flatten into single list
        players = []
        for idx in range(len(player_ids)):
            player_data = result.get(f"player_{idx}")
            if player_data:
                players.append(player_data)
        
        return players

    def get_teams(self, competition_id: str = None, limit: int = 500, page: int = 1) -> List[Dict[str, Any]]:
        """
        Get all teams with their details
        
        Args:
            competition_id: Filter by competition ID (optional)
            limit: Number of teams per page (default: 500)
            page: Page number (default: 1)
            
        Returns:
            List of team dictionaries
        """
        query = """
        query getClubs($pagination: PaginationInput, $filters: [ClubFilter!]) {
            getClubs(pagination: $pagination, filters: $filters) {
                meta { count pageCount currentPage }
                items {
                    id
                    name
                    brand
                }
            }
        }
        """
        
        filters = None
        if competition_id:
            filters = [{"competition": {"id": {"equals": competition_id}}}]
        
        variables = {
            "pagination": {"limit": limit, "page": page}
        }
        
        if filters:
            variables["filters"] = filters
        
        result = self.query(query, variables)
        return result.get("getClubs", {}).get("items", [])
