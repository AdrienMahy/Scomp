"""Persistence of downloaded SportsDynamics game payloads."""
import logging
from typing import Any, Dict, Optional

from ..models import Game
from .metadata_parser import parse_and_persist_lineups, parse_and_persist_periods
from .substitutions_parser import parse_and_persist_substitutions
from .player_distance_covered_parser import parse_and_persist_player_distance_covered
from .distance_covered_parser import parse_and_persist_distance_covered
from .fitness_entities_parser import parse_and_persist_fitness_entities
from .rgd_parser import parse_and_persist_rgd

logger = logging.getLogger(__name__)


class GamePayloadProcessor:
    """Parse and persist the optional JSON payloads for one game."""

    def __init__(self, db_session, task_id: Optional[str] = None):
        self.db_session = db_session
        self.task_id = task_id

    def process_metadata(self, game: Game, metadata_json: Dict[str, Any]) -> None:
        if not metadata_json:
            logger.info("No metadata JSON provided for game %s", game.id)
            return

        for label, parser in (
            ("lineups", parse_and_persist_lineups),
            ("periods", parse_and_persist_periods),
            ("substitutions", parse_and_persist_substitutions),
        ):
            try:
                logger.info("Processing %s for game %s", label, game.id)
                parser(game, metadata_json, self.db_session)
            except Exception as exc:
                logger.warning(
                    "Failed to process %s for %s: %s",
                    label,
                    game.id,
                    exc,
                    exc_info=True,
                )
                self.db_session.rollback()

    def build_player_to_team_mapping(
        self,
        metadata_json: Dict[str, Any],
    ) -> Dict[str, str]:
        if not metadata_json:
            return {}

        lineups = metadata_json.get("metadata", {}).get("lineups", [])
        mapping: Dict[str, str] = {}
        for lineup in lineups:
            team_id = lineup.get("id")
            for player_data in lineup.get("players", []):
                player_id = player_data.get("id")
                if player_id and team_id:
                    mapping[player_id] = team_id
        return mapping

    def process_distance(
        self,
        game: Game,
        distance_json: Dict[str, Any],
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not distance_json:
            logger.info("No distance_covered JSON data for game %s", game.id)
            return

        try:
            parse_and_persist_distance_covered(game, distance_json, self.db_session)
            team_mapping = self.build_player_to_team_mapping(metadata_json or {})
            parse_and_persist_player_distance_covered(
                game,
                distance_json,
                self.db_session,
                team_mapping=team_mapping,
            )
            self.db_session.commit()
        except Exception as exc:
            logger.warning(
                "Failed to process distance_covered for %s: %s",
                game.id,
                exc,
                exc_info=True,
            )
            self.db_session.rollback()

    def process_fitness(
        self,
        game: Game,
        fitness_json: Dict[str, Any],
    ) -> None:
        if not fitness_json:
            logger.info("No fitness_entities JSON data for game %s", game.id)
            return

        try:
            parse_and_persist_fitness_entities(
                game=game,
                fitness_data=fitness_json,
                db_session=self.db_session,
                calculate_summaries=True,
            )
            self.db_session.commit()
        except Exception as exc:
            logger.warning(
                "Failed to process fitness_entities for %s: %s",
                game.id,
                exc,
                exc_info=True,
            )
            self.db_session.rollback()

    def process_rgd(
        self,
        game: Game,
        game_name: str,
        rgd_json_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            result = parse_and_persist_rgd(
                game=game,
                game_name=game_name,
                db_session=self.db_session,
                rgd_json_data=rgd_json_data,
                clean_existing=True,
                task_id=self.task_id,
                round_name=game.round,
            )
            events, collective, individual, setpieces, errors = result
            entity_count = len((rgd_json_data or {}).get("entities", []))
            logger.info(
                "RGD processed for game %s: entities=%s, events=%s, "
                "collective=%s, individual=%s, setpieces=%s, errors=%s",
                game.id,
                entity_count,
                events,
                collective,
                individual,
                setpieces,
                errors,
            )
            if entity_count and not events:
                raise RuntimeError(
                    f"RGD contained {entity_count} entities but inserted no events"
                )
            self.db_session.commit()
        except Exception as exc:
            logger.warning(
                "Failed to process RGD for %s: %s",
                game.id,
                exc,
                exc_info=True,
            )
            self.db_session.rollback()
