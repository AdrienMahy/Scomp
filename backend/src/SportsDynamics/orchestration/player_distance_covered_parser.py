"""Player Distance Covered JSON Parser Module"""
import logging
import time
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import json

from src.SportsDynamics.models import Game, Player, PlayerDistanceCovered, LineupPlayer, LineupTeam

logger = logging.getLogger(__name__)


def parse_and_persist_player_distance_covered(
    game: Game,
    distance_data: dict,
    db_session: Session,
    team_mapping: dict = None,  # Optional: {player_id: team_id} mapping
) -> None:
    """
    Parse player-level distance_covered data and persist to database.
    
    JSON Structure:
    {
        "game_id": "...",
        "distance_unit": "m",
        "time_unit": "min",
        "speed_unit": "km_h",
        "speed_zones": [...],
        "players": [
            {
                "player_id": "p123",
                "minutes_played": 69.67,
                "total_distance_m": 8645.26,
                "distance_per_min_played_m": 124.1,
                "breakdowns": [
                    {
                        "category": {"speed_zone": "walking"},
                        "distance_m": 1919.25
                    },
                    {
                        "category": {"game_state": "in_play"},
                        "distance_m": 7200.50
                    },
                    {
                        "category": {"time_interval_5min": "0_5"},
                        "distance_m": 650.0
                    },
                    ...
                ]
            },
            ...
        ]
    }
    
    Args:
        game: Game instance
        distance_data: Parsed distance_covered.json dictionary
        db_session: SQLAlchemy session
        team_mapping: Optional dict mapping player_id to team_id for team assignment
    """
    try:
        players = distance_data.get("players", [])
        if not players:
            logger.warning(f"No players found in distance_covered for game {game.id}")
            return
        
        # Delete existing player distance records for this game (idempotency)
        db_session.query(PlayerDistanceCovered).filter(
            PlayerDistanceCovered.game_id == game.id
        ).delete()
        
        created_count = 0
        for player_data in players:
            # Skip if player_data is None or not a dict
            if not player_data or not isinstance(player_data, dict):
                logger.debug(f"Skipping invalid player_data: {player_data}")
                continue
            
            player_id = player_data.get("player_id")
            total_distance = player_data.get("total_distance_m")
            minutes_played = player_data.get("minutes_played")
            distance_per_min = player_data.get("distance_per_min_played_m")
            breakdowns = player_data.get("breakdowns", [])
            
            if not player_id or total_distance is None:
                logger.warning(f"Player distance missing player_id or total_distance: {player_data}")
                continue
            
            # Truncate ID fields to String(200) max (safety measure)
            player_id = str(player_id)[:200] if player_id else None
            if not player_id:
                logger.warning(f"player_id is empty after truncation")
                continue
            
            # Verify player exists in database
            player = db_session.query(Player).filter(Player.id == player_id).first()
            if not player:
                logger.warning(f"Player {player_id} not found in database for game {game.id}")
                continue
            
            # Determine team_id: Try mapping first, then lookup in LineupPlayer as fallback
            team_id = None
            if team_mapping and player_id in team_mapping:
                team_id = team_mapping[player_id]
            else:
                # Fallback: Lookup team_id from LineupTeam → LineupPlayer for this game and player
                lineup_player = (
                    db_session.query(LineupPlayer)
                    .join(LineupTeam)
                    .filter(
                        LineupTeam.game_id == game.id,
                        LineupPlayer.player_id == player_id
                    )
                    .first()
                )
                if lineup_player:
                    team_id = lineup_player.lineup_team.team_id
                    logger.debug(f"🔍 Looked up team_id {team_id} from LineupPlayer for player {player_id} in game {game.id}")
                else:
                    logger.warning(f"⚠️  Could not find team_id for player {player_id} in game {game.id}")
            
            # Extract speed zones, game state, and time intervals from breakdowns
            speed_zones = {}
            game_state = {}
            time_intervals = {}  # Changed to dict instead of list
            
            for breakdown in breakdowns:
                # Skip if breakdown is None or not a dict
                if not breakdown or not isinstance(breakdown, dict):
                    logger.debug(f"Skipping invalid breakdown: {breakdown}")
                    continue
                    
                category = breakdown.get("category", {})
                distance_m = breakdown.get("distance_m")
                
                if distance_m is None:
                    continue
                
                # Check if it's a speed zone
                if "speed_zone" in category:
                    speed_zone = category["speed_zone"]
                    speed_zones[speed_zone] = distance_m
                
                # Check if it's a game state
                if "game_state" in category:
                    state = category["game_state"]
                    game_state[state] = distance_m
                
                # Check if it's a time interval (convert to dict with category_name as key)
                if "time_interval_5min" in category:
                    time_interval = category["time_interval_5min"]
                    time_intervals[time_interval] = distance_m
            
            # Create PlayerDistanceCovered record with JSONB structure
            record_id = f"{game.id}_{player_id}"
            record_id = str(record_id)[:200] if record_id else str(uuid4())  # Truncate to String(200)
            
            try:
                distance_record = PlayerDistanceCovered(
                    id=record_id,
                    game_id=game.id,
                    player_id=player_id,
                    team_id=team_id,
                    metrics={
                        "total_distance_m": total_distance,
                        "distance_per_min_played_m": distance_per_min,
                        "minutes_played": minutes_played
                    },
                    speed_zones=speed_zones,
                    game_state=game_state,
                    time_intervals=time_intervals
                )
                db_session.add(distance_record)
                
                # Flush to catch database errors early
                db_session.flush()
                created_count += 1
                logger.info(f"✅ Created PlayerDistanceCovered for {player.name} in game {game.name} (team_id={team_id}, id={record_id[:50]}...)")
                
            except SQLAlchemyError as db_error:
                logger.error(f"❌ Database error creating PlayerDistanceCovered for player {player_id}: {db_error}")
                logger.error(f"   Record ID: {record_id}")
                logger.error(f"   Team ID: {team_id}")
                logger.error(f"   Data: {json.dumps(player_data, default=str, indent=2)}")
                raise
        
        logger.info(f"✅ Player distance covered parsed: {created_count}/{len(players)} players for game {game.id}")
        
    except Exception as e:
        logger.error(f"Error parsing player distance_covered for game {game.id}: {str(e)}", exc_info=True)
        raise
