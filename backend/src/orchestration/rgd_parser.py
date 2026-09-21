"""
RGD Parser Module

Parses RGD.json and persists structured event data to database:
- Events table (from all RGD entities with extraction of critical columns)
- Possession Collective table (from collective possession entities)
- Individual Possession table (from individual possession entities)

RGD (Reduced Game Data) contains:
- 3,000+ entities per match
- Events with critical metadata (player, team, possession, phase, etc.)
- Spatial coordinates and event timing
- Possession chains and sequences

Hybrid schema approach:
- Critical columns extracted for BTREE indices (fast jointures)
- Remaining data stored in JSONB sections (flexibility)
"""

import json
import logging
import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.models import Game, ScrapingLog, Setpieces
from src.etl.rgd_to_events_transformer import RGDToEventsTransformer
from src.etl.rgd_to_setpieces_transformer import RGDToSetpiecesTransformer

logger = logging.getLogger(__name__)


def _log_to_db(
    db_session: Session,
    task_id: Optional[str],
    message: str,
    level: str = "INFO",
    context: Optional[str] = None,
    item_id: Optional[str] = None,
    item_name: Optional[str] = None,
    round_name: Optional[str] = None,
    stats: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Insert a log entry into scraping_logs table for real-time frontend display.
    
    Args:
        db_session: SQLAlchemy session
        task_id: UUID of the scraping task (if None, log is skipped)
        message: Log message
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        context: Context type (game_cleaning, events, goals, etc.)
        item_id: ID of item being processed (game_id, etc.)
        item_name: Name/label of item (game name, etc.)
        round_name: Round number/name (e.g., "1", "J1", "Round 1")
        stats: Optional dict with table stats {"table_name": {"deleted": int, "inserted": int}}
    """
    if not task_id:
        return  # Skip if no task_id
    
    try:
        log = ScrapingLog(
            id=str(uuid4()),
            task_id=task_id,
            message=message,
            level=level,
            context=context,
            item_id=item_id,
            item_name=item_name,
            round=round_name,
            stats=stats,
        )
        db_session.add(log)
        db_session.flush()  # Write immediately to DB
    except Exception as e:
        logger.warning(f"Failed to log to DB: {e}")


def _clean_game_data(
    game_id: str,
    db_session: Session,
    task_id: Optional[str] = None,
    game_name: Optional[str] = None,
    round_name: Optional[str] = None,
) -> bool:
    """
    Delete a game and cascade-delete all related event data (23 tables).
    
    Uses manual deletion in reverse dependency order (leaf tables first).
    Ignores FK errors on individual table deletes to maximize cleanup.
    
    Args:
        game_id: UUID of the game to delete
        db_session: SQLAlchemy session
        task_id: Optional scraping task ID (for logging to DB)
        game_name: Optional game name (for logging)
        round_name: Optional round name (for logging)
    
    Returns:
        True if deleted, False if game not found
    """
    try:
        # Check if game exists
        game_exists = db_session.execute(
            text("SELECT 1 FROM games WHERE id = :gid"),
            {"gid": game_id}
        ).scalar()
        
        if not game_exists:
            logger.warning(f"⚠️  Game {game_id} not found, nothing to clean")
            return False
        
        logger.info(f"🧹 Cleaning existing game data before scraping")
        _log_to_db(db_session, task_id, f"🧹 Cleaning existing game data", 
                   context="game_cleaning", item_id=game_id, item_name=game_name, round_name=round_name)
        
        # Delete in reverse dependency order (leaf tables first)
        # Use NEW table names from migration 015 (game_goals, game_cards)
        # SKIP player_fitness_summary and team_fitness_summary - let calculate_fitness_summaries handle them
        # to avoid FK constraint issues
        tables_in_order = [
            'game_score_evolution', 'individual_possession', 'possession_collective', 
            'setpieces', 'ball_in_play', 'foul', 'goalkick', 'kickoff', 
            'offside', 'phase_of_play', 'type_of_play', 'events',
            'player_fitness_runs'
        ]
        
        deleted_count = 0
        for table in tables_in_order:
            try:
                result = db_session.execute(
                    text(f"DELETE FROM {table} WHERE game_id = :gid"),
                    {"gid": game_id}
                )
                if result.rowcount > 0:
                    deleted_count += result.rowcount
                    if table == 'setpieces':
                        logger.info(f"  🎯 DELETED {result.rowcount} setpieces from table")
                    else:
                        logger.info(f"  ✓ Deleted {result.rowcount} from {table}")
            except Exception as e:
                # Log but continue - FK violations are common during cleanup
                logger.info(f"  ⚠️  Could not clean {table}: {type(e).__name__}: {str(e)[:100]}")
                # Don't rollback individual table errors, just skip and continue
        
        # Finally delete the game itself
        # COMMENTED OUT: Don't delete the game record itself!
        # The game should survive - only the related data gets cleaned
        # db_session.execute(
        #     text("DELETE FROM games WHERE id = :gid"),
        #     {"gid": game_id}
        # )
        
        # Commit all deletes
        db_session.commit()
        
        logger.info(f"🧹 Cleaned game {game_id[:8]}... ({deleted_count} related records deleted)")
        _log_to_db(db_session, task_id, f"✓ Cleaned {deleted_count} related records", 
                   level="INFO", context="game_cleaning", item_id=game_id, item_name=game_name, round_name=round_name)
        return True
    
    except Exception as e:
        db_session.rollback()
        logger.error(f"❌ Failed to clean game data: {e}", exc_info=True)
        _log_to_db(db_session, task_id, f"❌ Failed to clean game data: {str(e)[:200]}", 
                   level="ERROR", context="game_cleaning", item_id=game_id, item_name=game_name, round_name=round_name)
        raise


def parse_and_persist_rgd(
    game: Game,
    game_name: str,
    db_session: Session,
    rgd_json_path: Optional[Path] = None,
    rgd_json_data: Optional[Dict] = None,
    clean_existing: bool = True,
    task_id: Optional[str] = None,
    round_name: Optional[str] = None,
) -> Tuple[int, int, int, int, int]:
    """
    Parse RGD.json and persist events and possession data to database.
    
    Args:
        game: Game ORM object
        game_name: Game name for directory organization
        db_session: SQLAlchemy session
        rgd_json_path: Optional custom path to rgd.json for legacy callers
        rgd_json_data: Optional in-memory RGD data (dict) - takes priority over rgd_json_path
        clean_existing: If True (DEFAULT), delete existing game data before scraping (CASCADE deletes all 23 related tables)
        task_id: Optional scraping task ID (for logging to DB)
        round_name: Optional round name (for logging)
    
    Returns:
        Tuple of (events_inserted, collective_possessions_inserted, 
                 individual_possessions_inserted, setpieces_inserted, errors)
    
    Tables updated:
    - events: ~3000 records per match
    - possession_collective: ~200 records per match
    - individual_possession: ~1200 records per match
    - setpieces: ~110 records per match
    - Plus 19 other specialized tables (goals, card, foul, ball_in_play, fitness data, etc.)
    """
    # Clean existing data before scraping (CASCADE deletes all 23 related tables)
    if clean_existing:
        logger.info(f"🧹 Cleaning existing game data before scraping")
        try:
            _clean_game_data(game.id, db_session, task_id=task_id, game_name=game_name, round_name=round_name)
        except Exception as e:
            logger.warning(f"⚠️  Cleaning failed, will keep old data and continue: {type(e).__name__}: {e}")
            _log_to_db(db_session, task_id, f"⚠️  Cleaning failed: {str(e)[:200]}", 
                       level="WARNING", context="game_cleaning", item_id=game.id, item_name=game_name, round_name=round_name)
            db_session.rollback()  # Rollback any partial deletes
    
    # Try to use in-memory data first (highest priority)
    if rgd_json_data:
        logger.info(f"ℹ️  Using in-memory RGD data for game {game_name}")
        rgd_json = rgd_json_data
    elif rgd_json_path and rgd_json_path.exists():
        try:
            # Load RGD JSON from disk
            with open(rgd_json_path, 'r', encoding='utf-8') as f:
                rgd_json = json.load(f)
        
            logger.info(f"✅ Loaded rgd.json for {game_name}")
            _log_to_db(db_session, task_id, f"✅ Loaded rgd.json", 
                       level="INFO", context="rgd_loading", item_id=game.id, item_name=game_name, round_name=round_name)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse rgd.json for {game_name}: {e}")
            _log_to_db(db_session, task_id, f"❌ Failed to parse rgd.json: {str(e)[:200]}", 
                       level="ERROR", context="rgd_parsing", item_id=game.id, item_name=game_name, round_name=round_name)
            return 0, 0, 0, 0
    else:
        logger.info(f"ℹ️  No rgd.json found for game {game_name}")
        _log_to_db(db_session, task_id, f"ℹ️  No rgd.json found", 
                   level="INFO", context="rgd_loading", item_id=game.id, item_name=game_name, round_name=round_name)
        return 0, 0, 0, 0
    
    try:
        # Extract entities
        entities = rgd_json.get("entities", [])
        logger.info(f"  📊 Found {len(entities)} RGD entities")
        
        # Initialize transformer
        transformer = RGDToEventsTransformer(game.id)
        
        # Separate entities by type
        event_entities = []
        collective_possessions = []
        individual_possessions = []
        setpiece_entities = []
        goal_entities = []
        card_entities = []
        substitution_entities = []
        foul_entities = []
        ball_in_play_entities = []
        goalkick_entities = []
        kickoff_entities = []
        offside_entities = []
        phase_of_play_entities = []
        type_of_play_entities = []
        
        for entity in entities:
            # Skip if entity is None or not a dict
            if not entity or not isinstance(entity, dict):
                logger.debug(f"Skipping invalid entity: {entity}")
                continue
            
            display_name = entity.get("gata_display_name", "").lower()
            
            # Route by display name
            if "individual possession" in display_name:
                individual_possessions.append(entity)
            elif "collective possession" in display_name or ("possession" in display_name and "individual" not in display_name):
                collective_possessions.append(entity)
            elif "goal" == display_name:
                goal_entities.append(entity)
            elif "card" == display_name:
                card_entities.append(entity)
            elif "substitution" == display_name:
                substitution_entities.append(entity)
            elif "foul" == display_name:
                foul_entities.append(entity)
            elif "ball in play" == display_name:
                ball_in_play_entities.append(entity)
            elif "goal-kick" in display_name or "goal kick" in display_name:
                goalkick_entities.append(entity)
            elif "kick-off" in display_name or "kick off" in display_name:
                kickoff_entities.append(entity)
            elif "offside" == display_name:
                offside_entities.append(entity)
            elif "attack vs" in display_name:
                # Attack vs High Block, Attack vs Mid Block, Attack vs Low Block → phase_of_play table
                phase_of_play_entities.append(entity)
            elif "structured play" == display_name or "fast play" == display_name:
                # Structured play, Fast play → type_of_play table
                type_of_play_entities.append(entity)
            elif any(pattern in display_name for pattern in [
                "free-kick", "free kick", "indirect free-kick", "indirect free kick",
                "corner", "corner kick",
                "throw-in", "throw in", "direct throw-in", "direct throw in"
            ]):
                # Set pieces (already handled by setpieces function)
                setpiece_entities.append(entity)
            else:
                # All other entities (passes, receiving runs, pressure, etc.) go to events
                event_entities.append(entity)
        
        # Add substitutions to generic events (no specialized table for them)
        event_entities.extend(substitution_entities)
        
        logger.info(f"  📑 Categorized entities:")
        logger.info(f"     - {len(event_entities)} for events table")
        logger.info(f"     - {len(goal_entities)} goals")
        logger.info(f"     - {len(card_entities)} cards")
        logger.info(f"     - {len(substitution_entities)} substitutions (→ events table, no specialized table)")
        logger.info(f"     - {len(foul_entities)} fouls")
        logger.info(f"     - {len(ball_in_play_entities)} ball in play")
        logger.info(f"     - {len(goalkick_entities)} goal kicks")
        logger.info(f"     - {len(kickoff_entities)} kick offs")
        logger.info(f"     - {len(offside_entities)} offsides")
        logger.info(f"     - {len(phase_of_play_entities)} phase of play")
        logger.info(f"     - {len(type_of_play_entities)} type of play")
        logger.info(f"     - {len(collective_possessions)} collective possessions")
        logger.info(f"     - {len(individual_possessions)} individual possessions")
        logger.info(f"     - {len(setpiece_entities)} set pieces")
        
        # Process generic events
        events_inserted = _persist_events(
            game, event_entities, transformer, db_session
        )
        
        # Process specialized event types
        # Note: Goals and Cards are now stored in events table with type filtering
        # Note: no specialized table for substitutions - kept in events table
        fouls_inserted = _persist_event_type("foul", game, foul_entities, db_session)
        ball_in_play_inserted = _persist_event_type("ball_in_play", game, ball_in_play_entities, db_session)
        goalkicks_inserted = _persist_event_type("goalkick", game, goalkick_entities, db_session)
        kickoffs_inserted = _persist_event_type("kickoff", game, kickoff_entities, db_session)
        offsides_inserted = _persist_event_type("offside", game, offside_entities, db_session)
        phase_of_play_inserted = _persist_event_type("phase_of_play", game, phase_of_play_entities, db_session)
        type_of_play_inserted = _persist_event_type("type_of_play", game, type_of_play_entities, db_session)
        
        # Process collective possessions
        collective_inserted = _persist_collective_possessions(
            game, collective_possessions, db_session
        )
        
        # Process individual possessions
        individual_inserted = _persist_individual_possessions(
            game, individual_possessions, db_session
        )
        
        # Process set pieces
        setpieces_inserted = _persist_setpieces(
            game, setpiece_entities, db_session
        )
        
        logger.info(f"")
        logger.info(f"╔════════════════════════════════════════════╗")
        logger.info(f"║  ✅ RGD PARSING COMPLETE - Data Inserted  ║")
        logger.info(f"╚════════════════════════════════════════════╝")
        logger.info(f"  📊 Summary of inserted rows:")
        logger.info(f"     📌 Events table: {events_inserted}")
        logger.info(f"     📌 Fouls table: {fouls_inserted}")
        logger.info(f"     📌 Ball in play table: {ball_in_play_inserted}")
        logger.info(f"     📌 Goal kicks table: {goalkicks_inserted}")
        logger.info(f"     📌 Kick offs table: {kickoffs_inserted}")
        logger.info(f"     📌 Offsides table: {offsides_inserted}")
        logger.info(f"     📌 Phase of play table: {phase_of_play_inserted}")
        logger.info(f"     📌 Type of play table: {type_of_play_inserted}")
        logger.info(f"     📌 Collective possessions table: {collective_inserted}")
        logger.info(f"     📌 Individual possessions table: {individual_inserted}")
        logger.info(f"     🎯 SETPIECES TABLE: {setpieces_inserted} ⭐")
        logger.info(f"")
        
        # Count errors from transformer
        errors = len(transformer.stats.get("errors", []))
        if errors:
            logger.warning(f"⚠️  {errors} transformation errors during RGD processing")
        
        return events_inserted, collective_inserted, individual_inserted, setpieces_inserted, errors
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse rgd.json for {game_name}: {e}")
        return 0, 0, 0, 0, 1
    except Exception as e:
        logger.error(f"❌ RGD processing error for {game_name}: {e}", exc_info=True)
        return 0, 0, 0, 0, 1


def _persist_events(
    game: Game,
    event_entities: list,
    transformer: RGDToEventsTransformer,
    db_session: Session,
) -> int:
    """
    Persist RGD entities directly to events table.
    
    RGD.json has flat entity structure, so we map directly without sections.
    Each RGD entity becomes an events record with:
    - Critical columns extracted for BTREE indices (player, team, possession, phase)
    - All remaining data stored in JSON column for flexibility
    - FK validation for missing references
    
    Args:
        game: Game ORM object
        event_entities: List of RGD entity dicts (flat structure from RGD.json)
        transformer: RGDToEventsTransformer instance (used for FK validation only)
        db_session: SQLAlchemy session
    
    Returns:
        Number of events inserted
    """
    if not event_entities:
        return 0
    
    def clean_uuid_field(value):
        """Convert invalid UUID values to None."""
        # Handle False, True, empty string, 'False', 'True', 'None'
        if isinstance(value, bool) or value is False or value is True:
            return None
        if isinstance(value, str) and value in ('', 'False', 'True', 'None', 'null'):
            return None
        return value
    
    try:
        now = datetime.utcnow()
        insert_values = []
        
        for entity in event_entities:
            # Create event record from RGD entity
            values = {
                "id": str(uuid4()),
                "game_id": game.id,
                "created_at": now,
                "updated_at": now,
                # Critical columns (extracted for BTREE indices)
                "period_id": entity.get("period_id"),
                "player_id": clean_uuid_field(entity.get("player_in_possession") or entity.get("passer") or entity.get("player")),
                "team_id": clean_uuid_field(entity.get("team")),
                "opponent_team_id": clean_uuid_field(entity.get("opponent_team")),
                "targeted_player_id": clean_uuid_field(entity.get("receiver") or entity.get("targeted_player")),
                "goalkeeper_id": clean_uuid_field(entity.get("goalkeeper")),
                "expected_defender_at_arrival_id": clean_uuid_field(entity.get("expected_defender_at_arrival")),
                "previous_passer_id": clean_uuid_field(entity.get("previous_passer")),
                # Phase jointure columns (UUIDs from RGD - may not exist in DB)
                "possession_id": clean_uuid_field(entity.get("possession")),
                "type_of_play_id": clean_uuid_field(entity.get("type_of_play")),
                "phase_of_play_id": clean_uuid_field(entity.get("phase_of_play")),
                "individual_possession_id": clean_uuid_field(entity.get("individual_possession")),
                # JSONB: store entire entity as-is (flat structure)
                "entity": json.dumps(entity),
            }
            
            # Note: FK validation to set invalid FKs to None
            values = _validate_event_fks(values, db_session)
            insert_values.append(values)
        
        # Batch insert
        if insert_values:
            columns = list(insert_values[0].keys())
            placeholders = ", ".join([f":{col}" for col in columns])
            columns_str = ", ".join(columns)
            
            insert_sql = f"""
                INSERT INTO events ({columns_str})
                VALUES ({placeholders})
            """
            
            db_session.execute(text(insert_sql), insert_values)
            logger.info(f"  ✅ Inserted {len(insert_values)} events from RGD")
            return len(insert_values)
    
    except Exception as e:
        logger.error(f"  ❌ Failed to insert RGD events: {e}", exc_info=True)
        raise
    
    return 0


def _persist_collective_possessions(
    game: Game,
    collective_entities: list,
    db_session: Session,
) -> int:
    """
    Persist collective possession entities to possession_collective table.
    
    Args:
        game: Game ORM object
        collective_entities: List of collective possession RGD entity dicts
        db_session: SQLAlchemy session
    
    Returns:
        Number of possessions inserted
    """
    if not collective_entities:
        return 0
    
    try:
        now = datetime.utcnow()
        insert_values = []
        
        for entity in collective_entities:
            # Extract critical columns
            values = {
                "id": entity.get("sequence_id", "").replace("-", "")[:50],  # Use sequence_id (unique) instead of entity_id
                "game_id": game.id,
                "period_id": entity.get("period_id"),
                "team_id": entity.get("team"),
                "opponent_team_id": entity.get("opponent_team"),
                "ball_in_play_id": None,  # Can be linked later if needed
                "created_at": now,
                "updated_at": now,
                # JSONB sections
                "entity": json.dumps({"gata_display_name": entity.get("gata_display_name")}),
                "time": json.dumps({
                    "start": entity.get("start"),
                    "end": entity.get("end"),
                    "duration": entity.get("duration"),
                    "start_frame": entity.get("start_frame"),
                    "end_frame": entity.get("end_frame"),
                }),
                "phase": json.dumps({
                    "possession": entity.get("possession"),
                    "context": entity.get("context"),
                    "play": entity.get("play"),
                    "phase_of_play": entity.get("phase_of_play"),
                }),
                "spatial": json.dumps({
                    "distance": entity.get("distance"),
                    "distance_gained": entity.get("distance_gained"),
                }),
                "actors": json.dumps({
                    "team": entity.get("team"),
                    "opponent_team": entity.get("opponent_team"),
                }),
                "possession": json.dumps({
                    "possession_id": entity.get("possession"),
                    "context": entity.get("context"),
                    "direction": entity.get("direction"),
                }),
            }
            
            # Validate team FKs (set to None if not in DB)
            for fk_col in ["team_id", "opponent_team_id"]:
                if values.get(fk_col):
                    if not _check_reference_exists(db_session, "teams", values[fk_col]):
                        values[fk_col] = None
            
            insert_values.append(values)
        
        # Batch insert
        if insert_values:
            columns = list(insert_values[0].keys())
            placeholders = ", ".join([f":{col}" for col in columns])
            columns_str = ", ".join(columns)
            
            insert_sql = f"""
                INSERT INTO possession_collective ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT(id) DO NOTHING
            """
            
            db_session.execute(text(insert_sql), insert_values)
            logger.info(f"  ✅ Inserted {len(insert_values)} collective possessions")
            return len(insert_values)
    
    except Exception as e:
        logger.error(f"  ❌ Failed to insert collective possessions: {e}")
        # Don't raise - allow ETL to continue
    
    return 0


def _persist_individual_possessions(
    game: Game,
    individual_entities: list,
    db_session: Session,
) -> int:
    """
    Persist individual possession entities to individual_possession table.
    
    Args:
        game: Game ORM object
        individual_entities: List of individual possession RGD entity dicts
        db_session: SQLAlchemy session
    
    Returns:
        Number of possessions inserted
    """
    if not individual_entities:
        return 0
    
    try:
        now = datetime.utcnow()
        insert_values = []
        
        for entity in individual_entities:
            # Extract critical columns
            values = {
                "id": entity.get("sequence_id", "").replace("-", "")[:50],  # Use sequence_id (unique) instead of entity_id
                "game_id": game.id,
                "period_id": entity.get("period_id"),
                "player_id": entity.get("player_in_possession"),
                "team_id": entity.get("team"),
                "created_at": now,
                "updated_at": now,
                # JSONB sections
                "entity": json.dumps({"gata_display_name": entity.get("gata_display_name")}),
                "time": json.dumps({
                    "start": entity.get("start"),
                    "end": entity.get("end"),
                    "duration": entity.get("duration"),
                    "start_frame": entity.get("start_frame"),
                    "end_frame": entity.get("end_frame"),
                }),
                "phase": json.dumps({
                    "possession": entity.get("possession"),
                    "context": entity.get("context"),
                }),
                "spatial": json.dumps({
                    "distance": entity.get("distance"),
                    "distance_gained": entity.get("distance_gained"),
                }),
                "actors": json.dumps({
                    "player_in_possession": entity.get("player_in_possession"),
                    "team": entity.get("team"),
                    "opponent_team": entity.get("opponent_team"),
                }),
            }
            
            # Validate player & team FKs (set to None if not in DB)
            for fk_col, fk_table in [("player_id", "players"), ("team_id", "teams")]:
                if values.get(fk_col):
                    if not _check_reference_exists(db_session, fk_table, values[fk_col]):
                        values[fk_col] = None
            
            insert_values.append(values)
        
        # Batch insert
        if insert_values:
            columns = list(insert_values[0].keys())
            placeholders = ", ".join([f":{col}" for col in columns])
            columns_str = ", ".join(columns)
            
            insert_sql = f"""
                INSERT INTO individual_possession ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT(id) DO NOTHING
            """
            
            db_session.execute(text(insert_sql), insert_values)
            logger.info(f"  ✅ Inserted {len(insert_values)} individual possessions")
            return len(insert_values)
    
    except Exception as e:
        logger.error(f"  ❌ Failed to insert individual possessions: {e}")
        # Don't raise - allow ETL to continue
    
    return 0


def _persist_setpieces(
    game: Game,
    setpiece_entities: list,
    db_session: Session,
) -> int:
    """
    Persist set piece entities to restructured setpieces table.
    
    Uses RGDToSetpiecesTransformer to:
    1. Determine type from gata_display_name (authoritative source)
    2. Extract critical columns for BTREE indices
    3. Build core JSONB sections (entity, time, spatial, actors, phase, channel)
    4. Route data to type-specific JSONB section (only ONE active per setpiece)
    
    Set pieces include:
    - Corner kicks
    - Free kicks (direct and indirect)
    - Throw-ins (direct and normal)
    - Kick-offs
    - Goal kicks
    
    Args:
        game: Game ORM object
        setpiece_entities: List of set piece RGD entity dicts
        db_session: SQLAlchemy session
    
    Returns:
        Number of set pieces inserted
    """
    if not setpiece_entities:
        logger.info(f"  ℹ️  No set pieces to process")
        return 0
    
    try:
        logger.info(f"  🎯 Processing {len(setpiece_entities)} set piece entities...")
        
        # Initialize transformer
        transformer = RGDToSetpiecesTransformer(game.id)
        
        # Transform RGD entities to SetpieceRecords
        setpiece_records, stats = transformer.transform_batch(setpiece_entities)
        
        logger.info(f"  📊 RGD Setpieces Transformer Stats:")
        logger.info(f"     - Total entities: {stats['total_entities']}")
        logger.info(f"     - By type: {stats['by_type']}")
        logger.info(f"     - Extracted columns: {dict(sorted((k, v) for k, v in stats['extracted_columns'].items() if v > 0))}")
        if stats['errors']:
            logger.warning(f"     - Errors: {len(stats['errors'])} (first 3: {stats['errors'][:3]})")
        
        # Batch insert transformed records as Setpiece ORM objects
        if setpiece_records:
            setpiece_models = []
            
            for record in setpiece_records:
                setpiece_model = Setpieces(
                    id=record.id,
                    game_id=record.game_id,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    # Critical extracted columns
                    period_id=record.period_id,
                    team_id=record.team_id,
                    opponent_team_id=record.opponent_team_id,
                    player_id=record.player_id,
                    gata_display_name=record.gata_display_name,
                    # Core JSONB sections
                    entity=record.entity,
                    time=record.time,
                    spatial=record.spatial,
                    actors=record.actors,
                    phase=record.phase,
                    channel=record.channel,
                    # Type-specific JSONB sections (only ONE is populated)
                    corner_kick=record.corner_kick,
                    free_kick=record.free_kick,
                    indirect_free_kick=record.indirect_free_kick,
                    throw_in=record.throw_in,
                    direct_throw_in=record.direct_throw_in,
                )
                setpiece_models.append(setpiece_model)
            
            # Batch add all records
            db_session.add_all(setpiece_models)
            db_session.flush()  # Ensure insert before returning count
            
            # Build detailed insertion summary
            inserted_count = len(setpiece_records)
            type_breakdown = ', '.join([
                f"{t}({stats['by_type'][t]})" 
                for t in sorted(stats['by_type'].keys()) 
                if stats['by_type'][t] > 0
            ])
            
            logger.info(f"")
            logger.info(f"  ✅ SETPIECES TABLE: {inserted_count} rows inserted")
            logger.info(f"     - Total inserted: {inserted_count} setpieces")
            logger.info(f"     - Breakdown by type: {type_breakdown}")
            logger.info(f"     - Indexed columns: team_id, player_id, gata_display_name, period_id")
            logger.info(f"     - JSONB sections: entity, time, spatial, actors, phase, channel + type-specific")
            logger.info(f"")
            
            return inserted_count
        else:
            logger.info(f"  ⚠️  No valid set pieces to insert after transformation")
            return 0
    
    except Exception as e:
        logger.error(f"  ❌ Failed to insert set pieces: {e}", exc_info=True)
        db_session.rollback()
        # Don't raise - allow ETL to continue
    
    return 0


def _persist_event_type(
    table_name: str,
    game: Game,
    event_entities: list,
    db_session: Session,
) -> int:
    """
    Generic function to persist RGD entities to specialized event tables.
    
    Dynamically adapts to table schema - inserts only columns that exist.
    Handles: goals, card, foul, ball_in_play, goalkick, kickoff, offside, 
             phase_of_play, type_of_play, etc.
    
    Args:
        table_name: Target table name (e.g., 'goals', 'ball_in_play')
        game: Game ORM object
        event_entities: List of RGD entity dicts
        db_session: SQLAlchemy session
    
    Returns:
        Number of entities inserted
    """
    if not event_entities:
        return 0
    
    def clean_uuid_field(value):
        """Convert invalid UUID values to None."""
        if isinstance(value, bool) or value is False or value is True:
            return None
        if isinstance(value, str) and value in ('', 'False', 'True', 'None', 'null'):
            return None
        return value
    
    try:
        now = datetime.utcnow()
        
        # SCHEMA INTROSPECTION
        # Different specialized event tables have different column structures:
        # - events table: uses 'period_id' (String FK to periods table)
        # - game_goals, game_cards: use 'period' (Integer: 1, 2, etc)
        # - Other tables: may have different optional columns
        # We introspect the actual table schema to determine which columns exist
        from sqlalchemy import inspect
        inspector = inspect(db_session.get_bind())
        table_columns = {col['name'] for col in inspector.get_columns(table_name)}
        
        insert_values = []
        
        for entity in event_entities:
            # Build base values that all event tables have
            values = {
                "id": str(uuid4()),
                "game_id": game.id,
                "created_at": now,
                "updated_at": now,
            }
            
            # COLUMN MAPPING FIX (2026-09-08)
            # Issue: Previous code always tried to insert 'period_id' for all tables,
            # but game_goals and game_cards don't have period_id column - they have 'period' (Integer)
            # This caused: UndefinedColumn error and cascade InFailedSqlTransaction
            # Solution: Detect which column exists and map appropriately
            if "period_id" in table_columns:
                values["period_id"] = entity.get("period_id")
            elif "period" in table_columns:
                values["period"] = entity.get("period")
            
            # Add optional columns if they exist in the target table
            if "player_id" in table_columns:
                values["player_id"] = clean_uuid_field(
                    entity.get("player_in_possession") or entity.get("passer") or entity.get("player")
                )
            if "team_id" in table_columns:
                values["team_id"] = clean_uuid_field(entity.get("team"))
            
            # All tables should have entity column (store entire entity as JSONB)
            if "entity" in table_columns:
                values["entity"] = json.dumps(entity)
            
            # Validate FKs to avoid constraint violations (set missing FKs to None)
            values = _validate_event_fks(values, db_session)
            
            insert_values.append(values)
        
        # Batch insert with dynamic column filtering
        if insert_values:
            # SCHEMA-AWARE INSERT FIX (2026-09-08)
            # Problem: Some event tables have optional columns we try to insert
            # (e.g., 'entity' in some tables but not others)
            # Solution: Only insert columns that actually exist in target table
            # This prevents UndefinedColumn errors on mixed-schema tables
            
            all_columns = set(insert_values[0].keys())
            existing_columns = [col for col in all_columns if col in table_columns]
            
            if not existing_columns:
                logger.error(f"  ❌ No valid columns found for {table_name}")
                return 0
            
            # Filter each row to only include columns that exist in target table
            filtered_values = []
            for row in insert_values:
                filtered_row = {k: v for k, v in row.items() if k in existing_columns}
                filtered_values.append(filtered_row)
            
            columns_str = ", ".join(existing_columns)
            placeholders = ", ".join([f":{col}" for col in existing_columns])
            
            insert_sql = f"""
                INSERT INTO {table_name} ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT(id) DO NOTHING
            """
            
            db_session.execute(text(insert_sql), filtered_values)
            logger.info(f"  ✅ Inserted {len(filtered_values)} records to {table_name} table")
            return len(filtered_values)
    
    except Exception as e:
        logger.error(f"  ❌ Failed to insert records to {table_name}: {e}", exc_info=True)
        # Don't raise - allow ETL to continue
    
    return 0


def _validate_event_fks(values: Dict[str, Any], db_session: Session) -> Dict[str, Any]:
    """
    Validate FK references in event values, setting to None if missing.
    
    Args:
        values: Event values dict from transformer
        db_session: SQLAlchemy session
    
    Returns:
        Updated values dict with validated FKs
    """
    # Player FK columns
    player_fk_columns = [
        "player_id", "targeted_player_id", "goalkeeper_id",
        "expected_defender_at_arrival_id", "previous_passer_id"
    ]
    
    for col in player_fk_columns:
        if values.get(col):
            if not _check_reference_exists(db_session, "players", values[col]):
                values[col] = None
    
    # Team FK columns
    team_fk_columns = ["team_id", "opponent_team_id"]
    
    for col in team_fk_columns:
        if values.get(col):
            if not _check_reference_exists(db_session, "teams", values[col]):
                values[col] = None
    
    # Phase/possession FK columns (optional, not validated against DB)
    # These are UUIDs but may not have corresponding records
    
    return values


def _check_reference_exists(
    db_session: Session,
    table_name: str,
    ref_id: str,
) -> bool:
    """
    Check if a reference ID exists in the database.
    
    Args:
        db_session: SQLAlchemy session
        table_name: Table to check (players, teams, etc.)
        ref_id: ID to check
    
    Returns:
        True if exists, False otherwise
    """
    try:
        result = db_session.execute(
            text(f"SELECT 1 FROM {table_name} WHERE id = :id LIMIT 1"),
            {"id": ref_id}
        ).scalar()
        return result is not None
    except Exception as e:
        logger.warning(f"Failed to check reference in {table_name}: {e}")
        return False
