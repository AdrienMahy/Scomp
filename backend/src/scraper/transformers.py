"""Data transformers from API response to ORM models"""
from typing import Dict, Any, Optional
from datetime import datetime
from ..models import Game, Team, Player, Club, Period, Squad


def transform_game(api_game: Dict[str, Any], competition_id: str, season_id: str) -> Game:
    """
    Transform API game response to ORM model
    
    Args:
        api_game: API response dict
        competition_id: Competition ID
        season_id: Season ID
        
    Returns:
        Game ORM instance
    """
    return Game(
        id=api_game.get("id"),
        competition_id=competition_id,
        season_id=season_id,
        name=api_game.get("name"),
        result=api_game.get("result"),
        home_team_id=api_game.get("homeTeam", {}).get("id"),
        away_team_id=api_game.get("awayTeam", {}).get("id"),
        home_score=api_game.get("homeScore"),
        away_score=api_game.get("awayScore"),
        home_team_formation=api_game.get("homeTeamFormation"),
        away_team_formation=api_game.get("awayTeamFormation"),
        starts_at=_parse_datetime(api_game.get("startsAt")),
        played_at=_parse_datetime(api_game.get("playedAt")),
        round_name=api_game.get("round", {}).get("name"),
        raw_data=api_game
    )


def transform_team(api_team: Dict[str, Any]) -> Team:
    """Transform API team to ORM model"""
    return Team(
        id=api_team.get("id"),
        name=api_team.get("name", api_team.get("brand", "")),
        brand=api_team.get("brand")
    )


def transform_club(api_club: Dict[str, Any]) -> Club:
    """Transform API club to ORM model"""
    provider_ids = {}
    for provider in api_club.get("providers", {}).get("items", []):
        provider_ids[provider.get("provider", {}).get("name")] = provider.get("externalId")
    
    return Club(
        id=api_club.get("id"),
        name=api_club.get("brand", ""),
        brand=api_club.get("brand"),
        logo_url=api_club.get("logoUrl"),
        provider_ids=provider_ids,
        raw_data=api_club
    )


def transform_player(api_player: Dict[str, Any], team_id: str) -> Player:
    """Transform API player to ORM model"""
    return Player(
        id=api_player.get("id"),
        team_id=team_id,
        first_name=api_player.get("firstName"),
        last_name=api_player.get("lastName"),
        name=api_player.get("name", api_player.get("usageName", "")),
        usage_name=api_player.get("usageName"),
        jersey_number=api_player.get("jerseyNumber"),
        raw_data=api_player
    )


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
