"""
Substitutions Parser Module

Parses substitution events from metadata.json and persists to game_substitutions table.

This module is separate from metadata_parser to keep each concern focused,
following the same pattern as distance_covered_parser and fitness_entities_parser.
"""

import logging
from uuid import uuid4
from sqlalchemy.orm import Session

from src.SportsDynamics.models import (
    Game,
    Player,
    GameSubstitution,
)

logger = logging.getLogger(__name__)


def parse_and_persist_substitutions(
    game: Game,
    metadata_json: dict,
    db_session: Session,
) -> None:
    """
    Parse metadata['events']['substitutions'] and persist GameSubstitution records.
    
    Metadata structure:
    {
        "events": {
            "substitutions": [
                {
                    "id": "s1",
                    "player_in_id": "p789",
                    "player_out_id": "p456",
                    "team_id": "t456",
                    "period": 2,
                    "frame": 48000,
                    "timestamp": 10.2
                },
                ...
            ]
        }
    }
    
    Args:
        game: Game instance
        metadata_json: Complete metadata dictionary
        db_session: SQLAlchemy session
    """
    try:
        # Handle both data formats:
        # Format 1: {"version": ..., "metadata": {"events": {}}} (from sportsdynamics_scraper)
        # Format 2: {"events": {}} (already extracted by scraper_coordinator)
        metadata = metadata_json.get("metadata", metadata_json)
        events = metadata.get("events", {})
        
        if not events:
            logger.warning(f"No events found in metadata for game {game.id}")
            return
        
        # Delete existing substitutions for this game (idempotency)
        db_session.query(GameSubstitution).filter(
            GameSubstitution.game_id == game.id
        ).delete(synchronize_session=False)
        
        # Process substitutions
        substitutions = events.get("substitutions", [])
        subs_inserted = 0
        
        for sub_data in substitutions:
            # Skip if substitution data is None or not a dict
            if not sub_data or not isinstance(sub_data, dict):
                logger.debug(f"Skipping invalid substitution: {sub_data}")
                continue
            
            sub_id = sub_data.get("id") or str(uuid4())
            player_in_id = sub_data.get("player_in_id")
            player_out_id = sub_data.get("player_out_id")
            team_id = sub_data.get("team_id")
            
            if not player_in_id or not player_out_id or not team_id:
                logger.warning(
                    f"Substitution missing required fields: "
                    f"player_in_id={player_in_id}, player_out_id={player_out_id}, team_id={team_id}"
                )
                continue
            
            # Verify players exist
            player_in = db_session.query(Player).filter(Player.id == player_in_id).first()
            player_out = db_session.query(Player).filter(Player.id == player_out_id).first()
            
            if not player_in or not player_out:
                logger.warning(
                    f"Substitution references non-existent players: "
                    f"in={player_in_id} (exists: {bool(player_in)}), "
                    f"out={player_out_id} (exists: {bool(player_out)})"
                )
                continue
            
            # Create GameSubstitution record
            substitution = GameSubstitution(
                id=sub_id,
                game_id=game.id,
                player_in_id=player_in_id,
                player_out_id=player_out_id,
                team_id=team_id,
                period=sub_data.get("period"),
                frame=sub_data.get("frame"),
                timestamp=sub_data.get("timestamp"),
            )
            db_session.add(substitution)
            subs_inserted += 1
        
        logger.info(
            f"⚽ Persisted substitution events for game {game.id}: {subs_inserted} substitutions"
        )
        
    except Exception as e:
        logger.error(f"❌ Error parsing substitutions for game {game.id}: {str(e)}", exc_info=True)
        raise
