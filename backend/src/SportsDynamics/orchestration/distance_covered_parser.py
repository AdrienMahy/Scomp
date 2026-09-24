"""Distance Covered JSON Parser Module"""
import logging
import time
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import json

from src.SportsDynamics.models import Game, Team, TeamDistanceCovered

logger = logging.getLogger(__name__)


def parse_and_persist_distance_covered(
    game: Game,
    distance_data: dict,
    db_session: Session,
) -> None:
    """
    Parse distance_covered.json and persist TeamDistanceCovered records.
    
    JSON Structure:
    {
        "game_id": "...",
        "distance_unit": "m",
        "time_unit": "min",
        "speed_unit": "km_h",
        "speed_zones": [...],
        "teams": [
            {
                "team_id": "t123",
                "total_distance_m": 117451.36,
                "breakdowns": [
                    {
                        "category": {"speed_zone": "walking"},
                        "distance_m": 33164.78
                    },
                    {
                        "category": {"game_state": "in_play"},
                        "distance_m": 92045.32
                    },
                    {
                        "category": {"time_interval_5min": "0_5"},
                        "distance_m": 7340.54
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
    """
    parser_start = time.time()
    try:
        logger.info(f"  📏 Parsing distance covered for {game.name}...")
        teams = distance_data.get("teams", [])
        if not teams:
            logger.warning(f"     ⚠️  No teams found in distance_covered for game {game.id}")
            return
        
        # Delete existing distance records for this game (idempotency)
        db_session.query(TeamDistanceCovered).filter(
            TeamDistanceCovered.game_id == game.id
        ).delete()
        
        created_count = 0
        for team_data in teams:
            # Skip if team_data is None or not a dict
            if not team_data or not isinstance(team_data, dict):
                logger.debug(f"Skipping invalid team_data: {team_data}")
                continue
            
            team_id = team_data.get("team_id")
            total_distance = team_data.get("total_distance_m")
            breakdowns = team_data.get("breakdowns", [])
            
            if not team_id or total_distance is None:
                logger.warning(f"Team distance missing team_id or total_distance: {team_data}")
                continue
            
            # Truncate ID fields to String(200) max (safety measure)
            team_id = str(team_id)[:200] if team_id else None
            if not team_id:
                logger.warning(f"team_id is empty after truncation")
                continue
            
            # Verify team exists in database
            team = db_session.query(Team).filter(Team.id == team_id).first()
            if not team:
                logger.warning(f"Team {team_id} not found in database for game {game.id}")
                continue
            
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
            
            # Create TeamDistanceCovered record with JSONB structure
            record_id = f"{game.id}_{team_id}"
            record_id = str(record_id)[:200] if record_id else str(uuid4())  # Truncate to String(200)
            
            try:
                distance_record = TeamDistanceCovered(
                    id=record_id,
                    game_id=game.id,
                    team_id=team_id,
                    metrics={
                        "total_distance_m": total_distance
                    },
                    speed_zones=speed_zones,
                    game_state=game_state,
                    time_intervals=time_intervals
                )
                db_session.add(distance_record)
                
                # Flush to catch database errors early
                db_session.flush()
                created_count += 1
                logger.info(f"✅ Created TeamDistanceCovered for {team.name} in game {game.name} (id={record_id[:50]}...)")
                
            except SQLAlchemyError as db_error:
                logger.error(f"❌ Database error creating TeamDistanceCovered for team {team_id}: {db_error}")
                logger.error(f"   Record ID: {record_id}")
                logger.error(f"   Data: {json.dumps(team_data, default=str, indent=2)}")
                raise
        
        parser_time = time.time() - parser_start
        logger.info(f"     ✅ Parsed: {created_count} teams ({parser_time:.1f}s)")
        
    except Exception as e:
        logger.error(f"Error parsing distance_covered for game {game.id}: {str(e)}", exc_info=True)
        raise
