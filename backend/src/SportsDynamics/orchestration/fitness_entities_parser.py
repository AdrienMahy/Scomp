"""Fitness Entities JSON Parser Module

Parses fitness_entities.json and persists PlayerFitnessRun records with relationships
to event tables (PossessionCollective, PhaseOfPlay, TypeOfPlay, IndividualPossession).

Handles 3,082+ Run entities per match with proper validation and error handling.
"""

import logging
import time
from uuid import uuid4
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.SportsDynamics.models import (
    Game,
    Player,
    Team,
    PlayerFitnessRun,
    PlayerFitnessSummary,
    TeamFitnessSummary,
)

logger = logging.getLogger(__name__)


def parse_and_persist_fitness_entities(
    game: Game,
    fitness_data: dict,
    db_session: Session,
    calculate_summaries: bool = True,
) -> None:
    """
    Parse fitness_entities.json and persist PlayerFitnessRun records.
    
    JSON Structure:
    {
        "version": "1.0",
        "config_version": "2.0",
        "export_type": "fitness",
        "generated_at": "2026-08-25T...",
        "game": {
            "game_id": "c1d63cc5-0585-4a32-b61a-77ce8df0c691",
            "coordinates_system": {...},
            "units": {...}
        },
        "entities": [
            {
                "sequence_id": "...",
                "entity_id": "...",
                "gata_display_name": "Run",
                "period_id": 1,
                "start": 0.04,          # start_time_s
                "end": 4.04,            # end_time_s
                "duration": 4.0,        # duration_s
                "start_frame": 1,
                "end_frame": 101,
                "player": "UUID",       # player_id
                "team": "UUID",         # team_id
                "opponent_team": "UUID", # opponent_team_id
                "possession": "UUID",   # possession_id (FK)
                "phase_of_play": "UUID", # phase_of_play_id (FK)
                "play": "UUID",         # type_of_play_id (FK)
                "individual_possession": null, # individual_possession_id (FK, nullable)
                "distance": 19.3,       # distance_m
                "average_speed": 17.2,  # average_speed
                "peak_speed": 22.49,    # peak_speed
                ...51 total fields
            }
        ]
    }
    
    Args:
        game: Game instance (must exist in DB)
        fitness_data: Parsed fitness_entities.json dictionary
        db_session: SQLAlchemy session
        calculate_summaries: If True, calculate player and team fitness summaries
    
    Raises:
        ValueError: If required game data is missing
        Exception: On database errors (logged and re-raised)
    """
    
    if not fitness_data:
        logger.warning(f"Empty fitness_entities data for game {game.id}")
        return
    
    try:
        # ====================================================================
        # VALIDATION & PREPARATION
        # ====================================================================
        
        game_info = fitness_data.get("game", {})
        entities = fitness_data.get("entities", [])
        
        if not entities:
            logger.warning(f"No fitness entities found for game {game.id}")
            return
        
        logger.info(f"Processing {len(entities)} fitness entities for game {game.id}")
        
        # Delete existing fitness records for this game (idempotency)
        db_session.query(PlayerFitnessRun).filter(
            PlayerFitnessRun.game_id == game.id
        ).delete(synchronize_session=False)
        
        # ====================================================================
        # PARSE & VALIDATE ENTITIES
        # ====================================================================
        
        runs_created = 0
        runs_skipped = 0
        missing_refs = {
            'possession': [],
            'phase_of_play': [],
            'type_of_play': [],
            'individual_possession': [],
        }
        
        for entity in entities:
            # Skip if entity is None or not a dict
            if not entity or not isinstance(entity, dict):
                logger.debug(f"Skipping invalid entity: {entity}")
                continue
            
            try:
                run_record = _transform_entity_to_run(
                    entity=entity,
                    game=game,
                    db_session=db_session,
                )
                
                if run_record is None:
                    runs_skipped += 1
                    continue
                
                db_session.add(run_record)
                runs_created += 1
                
                # Log missing event references (for data quality monitoring)
                possession_id = entity.get("possession")
                if possession_id and not _check_event_reference_exists(
                    db_session, "possession_collective", possession_id
                ):
                    missing_refs['possession'].append(possession_id)
                
                phase_of_play_id = entity.get("phase_of_play")
                if phase_of_play_id and not _check_event_reference_exists(
                    db_session, "phase_of_play", phase_of_play_id
                ):
                    missing_refs['phase_of_play'].append(phase_of_play_id)
                
                type_of_play_id = entity.get("play")
                if type_of_play_id and not _check_event_reference_exists(
                    db_session, "type_of_play", type_of_play_id
                ):
                    missing_refs['type_of_play'].append(type_of_play_id)
                
                individual_possession_id = entity.get("individual_possession")
                if individual_possession_id and not _check_event_reference_exists(
                    db_session, "individual_possession", individual_possession_id
                ):
                    missing_refs['individual_possession'].append(individual_possession_id)
                
            except Exception as e:
                logger.error(f"Error processing fitness entity: {str(e)}", exc_info=True)
                runs_skipped += 1
                continue
        
        # Batch insert all runs
        try:
            db_session.flush()
        except Exception as flush_error:
            # Capture detailed error info for debugging
            import traceback
            error_msg = str(flush_error)
            
            # Check if it's a StringDataRightTruncation error
            if "StringDataRightTruncation" in error_msg or "valeur trop longue" in error_msg:
                logger.error(f"🔴 StringDataRightTruncation during fitness flush: {error_msg}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Log sample of problematic records
                logger.error(f"Sample records created: {runs_created}, skipped: {runs_skipped}")
                raise
            else:
                logger.error(f"Error flushing fitness entities: {error_msg}")
                raise
        
        # ====================================================================
        # CALCULATE SUMMARIES (OPTIONAL)
        # ====================================================================
        
        if calculate_summaries and runs_created > 0:
            logger.info(f"Calculating fitness summaries for game {game.id}...")
            _calculate_fitness_summaries(game, db_session)
        
        # ====================================================================
        # LOG RESULTS
        # ====================================================================
        
        logger.info(
            f"✅ Fitness entities parsed: {runs_created} created, {runs_skipped} skipped "
            f"for game {game.id}"
        )
        
        # Log missing references (data quality monitoring)
        for ref_type, missing_ids in missing_refs.items():
            if missing_ids:
                unique_missing = set(missing_ids)
                logger.warning(
                    f"⚠️  Missing {ref_type} references: {len(unique_missing)} unique IDs "
                    f"(example: {list(unique_missing)[:3]})"
                )
        
    except Exception as e:
        logger.error(
            f"Error parsing fitness_entities for game {game.id}: {str(e)}",
            exc_info=True
        )
        raise


def _transform_entity_to_run(
    entity: Dict[str, Any],
    game: Game,
    db_session: Session,
) -> Optional[PlayerFitnessRun]:
    """
    Transform a single fitness entity to PlayerFitnessRun ORM object.
    
    Args:
        entity: Single fitness entity from fitness_entities.json
        game: Game instance
        db_session: SQLAlchemy session
    
    Returns:
        PlayerFitnessRun instance or None if validation fails
    """
    
    try:
        # ====================================================================
        # EXTRACT & VALIDATE REQUIRED FIELDS
        # ====================================================================
        
        player_id = entity.get("player")
        team_id = entity.get("team")
        opponent_team_id = entity.get("opponent_team")
        period_id = entity.get("period_id")
        
        if not all([player_id, team_id, opponent_team_id, period_id]):
            logger.warning(
                f"Missing required fields in fitness entity: "
                f"player={player_id}, team={team_id}, opponent={opponent_team_id}, "
                f"period={period_id}"
            )
            return None
        
        # Verify player & teams exist
        player = db_session.query(Player).filter(Player.id == player_id).first()
        if not player:
            logger.warning(f"Player {player_id} not found in database")
            return None
        
        team = db_session.query(Team).filter(Team.id == team_id).first()
        if not team:
            logger.warning(f"Team {team_id} not found in database")
            return None
        
        opponent_team = db_session.query(Team).filter(Team.id == opponent_team_id).first()
        if not opponent_team:
            logger.warning(f"Opponent team {opponent_team_id} not found in database")
            return None
        
        # ====================================================================
        # BUILD JSONB METADATA
        # ====================================================================
        
        metadata = _build_fitness_metadata(entity)
        
        # ====================================================================
        # VALIDATE FOREIGN KEY REFERENCES (SET TO NULL IF MISSING)
        # ====================================================================
        
        possession_id = entity.get("possession")
        if possession_id and not _check_event_reference_exists(db_session, "possession_collective", possession_id):
            logger.warning(f"Possession {possession_id} not found, setting to NULL")
            possession_id = None
        
        phase_of_play_id = entity.get("phase_of_play")
        if phase_of_play_id and not _check_event_reference_exists(db_session, "phase_of_play", phase_of_play_id):
            logger.warning(f"Phase of play {phase_of_play_id} not found, setting to NULL")
            phase_of_play_id = None
        
        type_of_play_id = entity.get("play")
        if type_of_play_id and not _check_event_reference_exists(db_session, "type_of_play", type_of_play_id):
            logger.warning(f"Type of play {type_of_play_id} not found, setting to NULL")
            type_of_play_id = None
        
        individual_possession_id = entity.get("individual_possession")
        if individual_possession_id and not _check_event_reference_exists(db_session, "individual_possession", individual_possession_id):
            logger.warning(f"Individual possession {individual_possession_id} not found, setting to NULL")
            individual_possession_id = None
        
        # ====================================================================
        # CREATE ORM OBJECT
        # ====================================================================
        
        # === TRUNCATE String(100) fields to avoid StringDataRightTruncation ===
        acceleration_intensity_level = entity.get("acceleration_intensity_level")
        if acceleration_intensity_level and len(str(acceleration_intensity_level)) > 100:
            logger.warning(f"⚠️ acceleration_intensity_level truncated from {len(str(acceleration_intensity_level))} to 100: {acceleration_intensity_level[:100]}")
            acceleration_intensity_level = str(acceleration_intensity_level)[:100]
        
        context = entity.get("context")
        if context and len(str(context)) > 100:
            logger.warning(f"⚠️ context truncated from {len(str(context))} to 100: {context[:100]}")
            context = str(context)[:100]
        
        direction = entity.get("direction")
        if direction and len(str(direction)) > 100:
            logger.warning(f"⚠️ direction truncated from {len(str(direction))} to 100: {direction[:100]}")
            direction = str(direction)[:100]
        
        phase_of_play_label = entity.get("phase_of_play_label")
        if phase_of_play_label and len(str(phase_of_play_label)) > 100:
            logger.warning(f"⚠️ phase_of_play_label truncated from {len(str(phase_of_play_label))} to 100: {phase_of_play_label[:100]}")
            phase_of_play_label = str(phase_of_play_label)[:100]
        
        play_label = entity.get("play_label")
        if play_label and len(str(play_label)) > 100:
            logger.warning(f"⚠️ play_label truncated from {len(str(play_label))} to 100: {play_label[:100]}")
            play_label = str(play_label)[:100]
        
        possession_label = entity.get("possession_label")
        if possession_label and len(str(possession_label)) > 100:
            logger.warning(f"⚠️ possession_label truncated from {len(str(possession_label))} to 100: {possession_label[:100]}")
            possession_label = str(possession_label)[:100]
        
        # === TRUNCATE spatial/channel fields ===
        start_third = entity.get("start_third")
        if start_third and len(str(start_third)) > 100:
            logger.warning(f"⚠️ start_third truncated from {len(str(start_third))} to 100: {start_third[:100]}")
            start_third = str(start_third)[:100]
        
        end_third = entity.get("end_third")
        if end_third and len(str(end_third)) > 100:
            logger.warning(f"⚠️ end_third truncated from {len(str(end_third))} to 100: {end_third[:100]}")
            end_third = str(end_third)[:100]
        
        start_channel = entity.get("start_channel")
        if start_channel and len(str(start_channel)) > 100:
            logger.warning(f"⚠️ start_channel truncated from {len(str(start_channel))} to 100: {start_channel[:100]}")
            start_channel = str(start_channel)[:100]
        
        end_channel = entity.get("end_channel")
        if end_channel and len(str(end_channel)) > 100:
            logger.warning(f"⚠️ end_channel truncated from {len(str(end_channel))} to 100: {end_channel[:100]}")
            end_channel = str(end_channel)[:100]
        
        functional_start_zone = entity.get("functional_start_zone")
        if functional_start_zone and len(str(functional_start_zone)) > 100:
            logger.warning(f"⚠️ functional_start_zone truncated from {len(str(functional_start_zone))} to 100: {functional_start_zone[:100]}")
            functional_start_zone = str(functional_start_zone)[:100]
        
        run = PlayerFitnessRun(
            id=str(uuid4()),
            game_id=game.id,
            period_id=period_id,
            player_id=player_id,
            team_id=team_id,
            opponent_team_id=opponent_team_id,
            
            # === EVENT REFERENCES (Foreign Keys) ===
            possession_id=possession_id,
            phase_of_play_id=phase_of_play_id,
            type_of_play_id=type_of_play_id,
            individual_possession_id=individual_possession_id,
            
            # === TIMING ===
            start_time_s=float(entity.get("start", 0)),
            end_time_s=float(entity.get("end", 0)),
            duration_s=float(entity.get("duration", 0)),
            start_frame=entity.get("start_frame"),
            end_frame=entity.get("end_frame"),
            
            # === DISTANCE ===
            distance_m=float(entity.get("distance", 0)),
            high_speed_distance_m=entity.get("high_speed_distance"),
            sprint_distance_m=entity.get("sprint_distance"),
            
            # === SPEED ===
            average_speed=entity.get("average_speed"),
            peak_speed=entity.get("peak_speed"),
            high_speed_duration=entity.get("high_speed_duration"),
            sprint_duration=entity.get("sprint_duration"),
            time_to_peak_speed=entity.get("time_to_peak_speed"),
            
            # === ACCELERATION ===
            acceleration_at_start=entity.get("acceleration_at_start"),
            peak_acceleration=entity.get("peak_acceleration"),
            peak_deceleration=entity.get("peak_deceleration"),
            acceleration_intensity=entity.get("acceleration_intensity"),
            acceleration_intensity_level=acceleration_intensity_level,
            
            # === TACTICAL ===
            context=context,
            direction=direction,
            phase_of_play_label=phase_of_play_label,
            play_label=play_label,
            possession_label=possession_label,
            
            # === SPATIAL ===
            start_x=entity.get("start_x"),
            start_y=entity.get("start_y"),
            end_x=entity.get("end_x"),
            end_y=entity.get("end_y"),
            start_third=start_third,
            end_third=end_third,
            start_channel=start_channel,
            end_channel=end_channel,
            
            # === BOOLEAN CLASSIFICATIONS ===
            high_speed_run=entity.get("high_speed_run", False),
            is_receiving_run=entity.get("is_receiving_run", False),
            sprint=entity.get("sprint", False),
            run_with_ball=entity.get("run_with_ball", False),
            on_ball_run=entity.get("on_ball_run", False),
            
            # === BOX & ZONE ENTRIES ===
            defensive_box_entry=entity.get("defensive_box_entry", False),
            offensive_box_entry=entity.get("offensive_box_entry", False),
            defensive_third_entry=entity.get("defensive_third_entry", False),
            offensive_third_entry=entity.get("offensive_third_entry", False),
            functional_start_zone=entity.get("functional_start_zone"),
            
            # === JSONB METADATA ===
            metadata_json=metadata,
        )
        
        return run
        
    except Exception as e:
        logger.error(f"Error transforming fitness entity: {str(e)}", exc_info=True)
        return None


def _build_fitness_metadata(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build JSONB metadata section from fitness entity.
    
    Extracts non-critical fields that are stored in JSONB for flexible querying.
    """
    
    return {
        "sustained_speeds": {
            "0_5s": entity.get("sustained_speed_0_5s"),
            "1m": entity.get("sustained_speed_1m"),
            "1s": entity.get("sustained_speed_1s"),
            "2m": entity.get("sustained_speed_2m"),
            "2s": entity.get("sustained_speed_2s"),
            "3m": entity.get("sustained_speed_3m"),
            "3s": entity.get("sustained_speed_3s"),
            "5m": entity.get("sustained_speed_5m"),
        },
        "timing": {
            "time_to_moderate_speed": entity.get("time_to_moderate_speed"),
            "time_to_high_speed": entity.get("time_to_high_speed"),
            "time_to_sprint": entity.get("time_to_sprint"),
        },
        "classification": {
            "high_speed_run": entity.get("high_speed_run"),
            "is_receiving_run": entity.get("is_receiving_run"),
            "sprint": entity.get("sprint"),
            "run_with_ball": entity.get("run_with_ball"),
            "on_ball_run": entity.get("on_ball_run"),
        },
        "box_entries": {
            "defensive_box_entry": entity.get("defensive_box_entry"),
            "offensive_box_entry": entity.get("offensive_box_entry"),
            "defensive_third_entry": entity.get("defensive_third_entry"),
            "offensive_third_entry": entity.get("offensive_third_entry"),
        },
        "tactical_zones": {
            "tactical_space_start": entity.get("tactical_space_start"),
            "tactical_subspace_start": entity.get("tactical_subspace_start"),
            "targeted_tactical_space": entity.get("targeted_tactical_space"),
            "targeted_tactical_subspace": entity.get("targeted_tactical_subspace"),
            "functional_start_zone": entity.get("functional_start_zone"),
            "functional_end_zone": entity.get("functional_end_zone"),
        },
        "api_ids": {
            "sequence_id": entity.get("sequence_id"),
            "entity_id": entity.get("entity_id"),
            "gata_display_name": entity.get("gata_display_name"),
        },
    }


def _check_event_reference_exists(
    db_session: Session,
    table_name: str,
    entity_id: str,
) -> bool:
    """
    Check if an event reference exists in the database.
    
    Args:
        db_session: SQLAlchemy session
        table_name: Table to check (possession_collective, phase_of_play, etc)
        entity_id: UUID to check
    
    Returns:
        True if exists, False otherwise
    """
    
    # Use raw SQL for simplicity (avoid circular imports with models)
    # Wrap SQL in text() for SQLAlchemy 2.0 compatibility
    from sqlalchemy import text
    result = db_session.execute(
        text(f"SELECT 1 FROM {table_name} WHERE id = :entity_id LIMIT 1"),
        {"entity_id": entity_id}
    ).fetchone()
    
    return result is not None


def _calculate_fitness_summaries(
    game: Game,
    db_session: Session,
) -> None:
    """
    Calculate PlayerFitnessSummary and TeamFitnessSummary records.
    
    Args:
        game: Game instance
        db_session: SQLAlchemy session
    """
    
    try:
        # Delete existing summaries (idempotency)
        db_session.query(TeamFitnessSummary).filter(
            TeamFitnessSummary.game_id == game.id
        ).delete()
        db_session.query(PlayerFitnessSummary).filter(
            PlayerFitnessSummary.game_id == game.id
        ).delete()
        
        # ====================================================================
        # PLAYER SUMMARIES
        # ====================================================================
        
        runs = db_session.query(PlayerFitnessRun).filter(
            PlayerFitnessRun.game_id == game.id
        ).all()
        
        player_stats = {}
        team_stats = {}
        
        for run in runs:
            player_key = (run.game_id, run.player_id, run.team_id)
            if player_key not in player_stats:
                player_stats[player_key] = {
                    'total_runs': 0,
                    'total_distance_m': 0.0,
                    'total_high_speed_distance_m': 0.0,
                    'total_sprint_distance_m': 0.0,
                    'speeds': [],
                    'high_speed_run_count': 0,
                    'sprint_count': 0,
                    'receiving_run_count': 0,
                    'offensive_runs': 0,
                    'defensive_runs': 0,
                }
            
            stats = player_stats[player_key]
            stats['total_runs'] += 1
            stats['total_distance_m'] += run.distance_m or 0
            stats['total_high_speed_distance_m'] += run.high_speed_distance_m or 0
            stats['total_sprint_distance_m'] += run.sprint_distance_m or 0
            
            if run.peak_speed:
                stats['speeds'].append(run.peak_speed)
            
            if run.high_speed_run:
                stats['high_speed_run_count'] += 1
            if run.sprint:
                stats['sprint_count'] += 1
            if run.is_receiving_run:
                stats['receiving_run_count'] += 1
            
            if run.context == 'OFFENSIVE':
                stats['offensive_runs'] += 1
            elif run.context == 'DEFENSIVE':
                stats['defensive_runs'] += 1
            
            # Track team stats
            team_key = (run.game_id, run.team_id)
            if team_key not in team_stats:
                team_stats[team_key] = {
                    'total_runs': 0,
                    'total_distance_m': 0.0,
                    'total_high_speed_distance_m': 0.0,
                    'total_sprint_distance_m': 0.0,
                    'speeds': [],
                    'players': set(),
                    'offensive_runs': 0,
                    'defensive_runs': 0,
                }
            
            tstats = team_stats[team_key]
            tstats['total_runs'] += 1
            tstats['total_distance_m'] += run.distance_m or 0
            tstats['total_high_speed_distance_m'] += run.high_speed_distance_m or 0
            tstats['total_sprint_distance_m'] += run.sprint_distance_m or 0
            if run.peak_speed:
                tstats['speeds'].append(run.peak_speed)
            tstats['players'].add(run.player_id)
            if run.context == 'OFFENSIVE':
                tstats['offensive_runs'] += 1
            elif run.context == 'DEFENSIVE':
                tstats['defensive_runs'] += 1
        
        # Create PlayerFitnessSummary records
        for (game_id, player_id, team_id), stats in player_stats.items():
            summary = PlayerFitnessSummary(
                id=str(uuid4()),
                game_id=game_id,
                player_id=player_id,
                team_id=team_id,
                total_runs=stats['total_runs'],
                total_distance_m=stats['total_distance_m'],
                total_high_speed_distance_m=stats['total_high_speed_distance_m'],
                total_sprint_distance_m=stats['total_sprint_distance_m'],
                average_run_speed_ms=sum(stats['speeds']) / len(stats['speeds']) if stats['speeds'] else None,
                peak_speed_ms=max(stats['speeds']) if stats['speeds'] else None,
                high_speed_run_count=stats['high_speed_run_count'],
                sprint_count=stats['sprint_count'],
                receiving_run_count=stats['receiving_run_count'],
                offensive_runs=stats['offensive_runs'],
                defensive_runs=stats['defensive_runs'],
            )
            db_session.add(summary)
        
        # ====================================================================
        # TEAM SUMMARIES
        # ====================================================================
        
        for (game_id, team_id), stats in team_stats.items():
            summary = TeamFitnessSummary(
                id=str(uuid4()),
                game_id=game_id,
                team_id=team_id,
                total_runs=stats['total_runs'],
                total_distance_m=stats['total_distance_m'],
                total_high_speed_distance_m=stats['total_high_speed_distance_m'],
                total_sprint_distance_m=stats['total_sprint_distance_m'],
                average_team_speed_ms=sum(stats['speeds']) / len(stats['speeds']) if stats['speeds'] else None,
                players_tracked=len(stats['players']),
                offensive_runs=stats['offensive_runs'],
                defensive_runs=stats['defensive_runs'],
                average_runs_per_phase=stats['total_runs'] / 14 if stats['total_runs'] > 0 else 0,  # 14 phases per game avg
            )
            db_session.add(summary)
        
        logger.info(
            f"Calculated {len(player_stats)} player + {len(team_stats)} team fitness summaries "
            f"for game {game.id}"
        )
        
    except Exception as e:
        logger.error(f"Error calculating fitness summaries for game {game.id}: {str(e)}", exc_info=True)
        raise
