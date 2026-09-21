"""
Metadata JSON Parser Module
Parses metadata.json files and persists structured data to database:
- Lineups (from metadata['lineups'])
- Periods (from metadata['periods']) with score evolution

Note: Events parsing has been moved to events_parser.py module
"""

import logging
import time
from typing import Optional
from uuid import NAMESPACE_URL, uuid4, uuid5
from datetime import datetime
from sqlalchemy.orm import Session

from src.models import (
    Game,
    Player,
    Team,
    LineupTeam,
    LineupPlayer,
    Period,
    GameScoreEvolution,
)

# Import substitutions parser
from .substitutions_parser import parse_and_persist_substitutions

logger = logging.getLogger(__name__)


def _stable_lineup_id(game_id: str, team_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"scomp:lineup-team:{game_id}:{team_id}"))


def _stable_lineup_player_id(game_id: str, team_id: str, player_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"scomp:lineup-player:{game_id}:{team_id}:{player_id}"))


def parse_and_persist_lineups(
    game: Game,
    metadata_json: dict,
    db_session: Session,
) -> None:
    """
    Parse metadata['lineups'] and persist LineupTeam/LineupPlayer records.
    
    Metadata structure:
    {
        "lineups": [
            {
                "ground": "home",  # or "away"
                "team_id": "t123",
                "team_name": "Team A",
                "players": [
                    {
                        "player_id": "p456",
                        "player_name": "John Doe",
                        "starter": true,
                        "substitute": false,
                        "playing_time": 90,
                        "jersey": 7,
                        "position": "FW",
                        "individual_possession": 45.2
                    },
                    ...
                ]
            },
            ...
        ]
    }
    
    Args:
        game: Game instance to associate lineups with
        metadata_json: Complete metadata dictionary
        db_session: SQLAlchemy session for database operations
    """
    parser_start = time.time()
    try:
        logger.info(f"  📋 Parsing lineups for {game.name}...")
        # Handle both data formats:
        # Format 1: {"version": ..., "metadata": {"lineups": [...]}} (from sportsdynamics_scraper)
        # Format 2: {"lineups": [...]} (already extracted by scraper_coordinator)
        metadata = metadata_json.get("metadata", metadata_json)

        # The schedule API can omit scores while metadata.json contains the
        # authoritative final score for the processed match.
        final_score = metadata.get("final_score") or {}
        home_score = final_score.get("home")
        away_score = final_score.get("away")
        if home_score is not None and away_score is not None:
            game.home_score = home_score
            game.away_score = away_score
            if home_score > away_score:
                game.result = "HOME_TEAM_WIN"
            elif away_score > home_score:
                game.result = "AWAY_TEAM_WIN"
            else:
                game.result = "DRAW"
            db_session.add(game)
            db_session.commit()
            logger.info(
                "     ✅ Updated game score from metadata: %s-%s (%s)",
                home_score,
                away_score,
                game.result,
            )

        lineups = metadata.get("lineups", [])
        if not lineups:
            logger.warning(f"     ⚠️  No lineups found in metadata for game {game.id}")
            return
        
        # Delete existing lineups for this game (idempotency)
        db_session.query(LineupPlayer).filter(
            LineupPlayer.lineup_team.has(game_id=game.id)
        ).delete()
        db_session.query(LineupTeam).filter(LineupTeam.game_id == game.id).delete()
        
        lineup_teams_created = 0
        lineup_players_created = 0
        
        for lineup_data in lineups:
            ground = lineup_data.get("ground")  # "home" or "away"
            team_id = lineup_data.get("id")  # Team UUID from JSON "id" field
            team_name = lineup_data.get("name")  # Team name from JSON
            possession = lineup_data.get("possession")  # Ball possession percentage
            players = lineup_data.get("players", [])
            
            if not team_id:
                logger.warning(f"Lineup missing team id: {lineup_data}")
                continue

            if len(players) < 11:
                logger.warning(
                    f"⚠️ Incomplete lineup for {team_name or team_id} in game {game.id}: "
                    f"{len(players)} players found"
                )
            
            # Verify team exists in database, CREATE if missing
            team = db_session.query(Team).filter(Team.id == team_id).first()
            if not team:
                logger.info(f"Creating missing team: {team_name} (id={team_id})")
                team = Team(
                    id=team_id,
                    name=team_name or f"Team {team_id[:8]}",
                    competition_id=game.competition_id,
                    brand=team_name or f"Team {team_id[:8]}"
                )
                db_session.add(team)
                db_session.flush()  # Flush so FK references work
            
            # Create LineupTeam entry
            lineup_team = LineupTeam(
                id=_stable_lineup_id(game.id, team_id),
                game_id=game.id,
                team_id=team_id,
                position=ground.upper() if ground else None,  # "HOME" or "AWAY"
                possession=possession,  # Ball possession percentage
            )
            db_session.add(lineup_team)
            db_session.flush()  # Flush to get lineup_team.id
            lineup_teams_created += 1
            
            # Create LineupPlayer entries
            for player_data in players:
                # Skip if player data is None or not a dict
                if not player_data or not isinstance(player_data, dict):
                    logger.debug(f"Skipping invalid player data: {player_data}")
                    continue
                
                player_id = player_data.get("id")  # Player UUID from JSON "id" field
                
                if not player_id:
                    logger.warning(f"Player missing id: {player_data}")
                    continue
                
                # Create a minimal player record when metadata arrives first.
                player = db_session.query(Player).filter(Player.id == player_id).first()
                if not player:
                    player_name = (
                        player_data.get("name")
                        or player_data.get("usage_name")
                        or player_data.get("usageName")
                        or f"Player {player_id[:8]}"
                    )
                    player = Player(
                        id=player_id,
                        first_name=player_data.get("first_name") or player_data.get("firstName"),
                        last_name=player_data.get("last_name") or player_data.get("lastName"),
                        name=player_name,
                        usage_name=player_data.get("usage_name") or player_data.get("usageName"),
                    )
                    db_session.add(player)
                    db_session.flush()
                    logger.info(f"     ➕ Created player {player_name} ({player_id})")
                
                lineup_player = LineupPlayer(
                    id=_stable_lineup_player_id(game.id, team_id, player_id),
                    lineup_team_id=lineup_team.id,
                    player_id=player_id,
                    starting=player_data.get("starter", False),  # JSON has "starter" field → DB column "starting"
                    is_substitute=player_data.get("substitute", False),  # JSON "substitute" → DB "is_substitute"
                    shirt_number=player_data.get("jersey"),  # JSON "jersey" → DB "shirt_number"
                    playing_time=player_data.get("playing_time"),  # JSON "playing_time" → DB "playing_time" (Float)
                    individual_possession=player_data.get("individual_possession"),  # JSON "individual_possession" → DB "individual_possession" (Float)
                    position=None,  # Not populated from JSON
                )
                db_session.add(lineup_player)
                lineup_players_created += 1
        
        # Explicit commit for lineups
        if lineup_teams_created > 0 or lineup_players_created > 0:
            try:
                logger.info(f"     🔄 ABOUT TO COMMIT: 2 teams, {lineup_players_created} players for game {game.id}")
                db_session.commit()
                parser_time = time.time() - parser_start
                logger.info(f"     ✅✅✅ COMMIT SUCCESSFUL: Persisted 2 teams, {lineup_players_created} players ({parser_time:.1f}s)")
                
                # Verify data actually exists in DB
                verification_teams = db_session.query(LineupTeam).filter(LineupTeam.game_id == game.id).count()
                verification_players = db_session.query(LineupPlayer).join(
                    LineupTeam, LineupPlayer.lineup_team_id == LineupTeam.id
                ).filter(LineupTeam.game_id == game.id).count()
                logger.info(f"     🔍 VERIFICATION: Query shows {verification_teams} teams and {verification_players} players in DB for game {game.id}")
            except Exception as e:
                logger.error(f"❌❌❌ COMMIT FAILED for lineups in game {game.id}: {e}")
                db_session.rollback()
                raise
        else:
            parser_time = time.time() - parser_start
            logger.warning(f"     ⚠️  No lineups created for game {game.id} ({parser_time:.1f}s)")
        
    except Exception as e:
        parser_time = time.time() - parser_start
        logger.error(f"Error parsing lineups for game {game.id} ({parser_time:.1f}s): {str(e)}", exc_info=True)
        raise


def parse_and_persist_periods(
    game: Game,
    metadata_json: dict,
    db_session: Session,
) -> None:
    """
    Parse metadata['periods'] and persist Period + GameScoreEvolution records.
    
    Metadata structure:
    {
        "periods": [
            {
                "id": 1,
                "start_frame": 0,
                "end_frame": 45000,
                "duration": 45.5,
                "home_team_direction": "ltr",
                "away_team_direction": "rtl",
                "current_score": "0-0",
                "score_evolution": [
                    {"score": "0-0", "score_home": 0, "score_away": 0, "frame_start": 0, "frame_end": 1000},
                    {"score": "1-0", "score_home": 1, "score_away": 0, "frame_start": 1000, "frame_end": 45000},
                    ...
                ]
            },
            ...
        ]
    }
    
    Args:
        game: Game instance
        metadata_json: Complete metadata dictionary
        db_session: SQLAlchemy session
    """
    try:
        # Handle both data formats:
        # Format 1: {"version": ..., "metadata": {"periods": [...]}} (from sportsdynamics_scraper)
        # Format 2: {"periods": [...]} (already extracted by scraper_coordinator)
        metadata = metadata_json.get("metadata", metadata_json)
        periods = metadata.get("periods", [])
        
        # DEBUG: Always log metadata structure
        logger.info(f"DEBUG: metadata keys for game {game.id}: {list(metadata.keys()) if metadata else 'empty'}")
        logger.info(f"DEBUG: periods found for game {game.id}: {len(periods) if periods else 0} periods")
        if periods:
            logger.info(f"DEBUG: First period keys: {list(periods[0].keys())}")
            logger.info(f"DEBUG: First period data: {periods[0]}")
        
        if not periods:
            logger.warning(f"No periods found in metadata for game {game.id}")
            return
        
        # Delete existing periods for this game (idempotency)
        logger.info(f"🧹 Cleaning existing game data before scraping")
        db_session.query(GameScoreEvolution).filter(GameScoreEvolution.game_id == game.id).delete()
        db_session.query(Period).filter(Period.game_id == game.id).delete()
        db_session.flush()  # Ensure DELETE is executed before INSERT
        logger.info(f"🧹 Cleaned existing periods and score evolutions for game {game.id}")
        
        periods_created = 0
        score_evolutions_created = 0
        
        for period_data in periods:
            period_id = period_data.get("period", 0)  # Use "period" key instead of "id"
            start_frame = period_data.get("start_frame")
            end_frame = period_data.get("end_frame")
            duration = period_data.get("duration")
            home_direction = period_data.get("home_team_direction", "LTR").upper()
            away_direction = period_data.get("away_team_direction", "RTL").upper()
            score_evolution = period_data.get("score_evolution", {})  # Dict, not list
            
            # Build time JSONB structure
            logger.info(f"  📝 Creating Period {period_id} for game {game.id[:8]}...")
            logger.info(f"     - start_frame={start_frame}, end_frame={end_frame}, duration={duration}")
            logger.info(f"     - home_direction={home_direction}, away_direction={away_direction}")
            time_data = {
                "start_frame": start_frame,
                "end_frame": end_frame,
                "duration": duration,
            }
            
            # Build direction JSONB array structure
            # Each team has: {"team_id": "...", "value": "LTR"/"RTL", "coef": 1/-1}
            direction_data = [
                {
                    "team_id": game.home_team_id,
                    "value": home_direction,
                    "coef": -1 if home_direction == "LTR" else 1
                },
                {
                    "team_id": game.away_team_id,
                    "value": away_direction,
                    "coef": -1 if away_direction == "LTR" else 1
                }
            ]
            
            # Create Period record
            period = Period(
                id=str(uuid4()),
                game_id=game.id,
                period_id=period_id,
                time=time_data,
                direction=direction_data,
            )
            db_session.add(period)
            db_session.flush()  # Get period.id
            logger.info(f"     ✅ Period {period_id} created & flushed:")
            logger.info(f"        - period.time = {period.time}")
            logger.info(f"        - period.direction = {period.direction}")
            periods_created += 1
            
            # Process score evolution entries
            # score_evolution is a dict with score strings as keys: {"0-0": {...}, "1-0": {...}, ...}
            for score_str, evolution_data in score_evolution.items():
                try:
                    # Parse score string (e.g., "0-0" -> home=0, away=0)
                    score_parts = score_str.split("-")
                    score_home = int(score_parts[0]) if len(score_parts) > 0 else 0
                    score_away = int(score_parts[1]) if len(score_parts) > 1 else 0
                    
                    # Extract frame and timestamp arrays
                    frame_data = evolution_data.get("frame", [])
                    timestamp_data = evolution_data.get("timestamp", [])
                    
                    frame_start = frame_data[0] if len(frame_data) > 0 else None
                    frame_end = frame_data[1] if len(frame_data) > 1 else None
                    timestamp_start = timestamp_data[0] if len(timestamp_data) > 0 else None
                    timestamp_end = timestamp_data[1] if len(timestamp_data) > 1 else None
                    
                    # Create GameScoreEvolution entry
                    evolution = GameScoreEvolution(
                        id=str(uuid4()),
                        period_id=period.id,
                        game_id=game.id,
                        score=score_str,
                        score_home=score_home,
                        score_away=score_away,
                        frame_start=frame_start,
                        frame_end=frame_end,
                        timestamp_start=timestamp_start,
                        timestamp_end=timestamp_end,
                    )
                    db_session.add(evolution)
                    score_evolutions_created += 1
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing score evolution '{score_str}' for game {game.id}: {str(e)}")
        
        # Explicit commit for periods and score evolution
        if periods_created > 0 or score_evolutions_created > 0:
            try:
                logger.info(f"🔄 ABOUT TO COMMIT: {periods_created} periods + {score_evolutions_created} score evolutions for game {game.id}")
                db_session.commit()
                logger.info(f"✅✅✅ COMMIT SUCCESSFUL: Persisted periods for game {game.id}: {periods_created} periods, {score_evolutions_created} score evolutions")
                
                # Verify data actually exists in DB
                verification_count = db_session.query(Period).filter(Period.game_id == game.id).count()
                logger.info(f"🔍 VERIFICATION: Query shows {verification_count} periods now in DB for game {game.id}")
            except Exception as e:
                logger.error(f"❌❌❌ COMMIT FAILED for game {game.id}: {e}")
                db_session.rollback()
                raise
        else:
            logger.warning(f"⚠️  No periods created for game {game.id}")
        
    except Exception as e:
        logger.error(f"Error parsing periods for game {game.id}: {str(e)}", exc_info=True)
        raise


# Note: parse_and_persist_events has been moved to events_parser.py module
# It's re-exported above for backward compatibility
