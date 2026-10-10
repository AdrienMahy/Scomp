"""Persistence of downloaded SportsDynamics game payloads."""
import logging
from typing import Any, Dict, List, Optional

from ..models import (
    Game,
    LineupPlayer,
    LineupTeam,
    Player,
    PlayerFitnessRun,
    Team,
)
from .metadata_parser import parse_and_persist_lineups, parse_and_persist_periods
from .substitutions_parser import parse_and_persist_substitutions
from .player_distance_covered_parser import parse_and_persist_player_distance_covered
from .distance_covered_parser import parse_and_persist_distance_covered
from .fitness_entities_parser import (
    has_fitness_run_references,
    parse_and_persist_fitness_entities,
)
from .rgd_parser import parse_and_persist_goals, parse_and_persist_rgd

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

    def process_selected_parser(
        self,
        game: Game,
        parser_name: str,
        downloaded_data: Dict[str, Any],
    ) -> None:
        """Run one selected parser without invoking any sibling parser."""
        if parser_name == "lineups":
            metadata = self._required_payload(downloaded_data, "metadata")
            self._validate_lineup_payload(metadata)
            parse_and_persist_lineups(
                game,
                metadata,
                self.db_session,
                update_game_score=False,
                create_missing_entities=False,
            )
        elif parser_name == "periods":
            parse_and_persist_periods(
                game,
                self._required_payload(downloaded_data, "metadata"),
                self.db_session,
            )
        elif parser_name == "substitutions":
            metadata = self._required_payload(downloaded_data, "metadata")
            self._validate_substitution_references(game, metadata)
            parse_and_persist_substitutions(game, metadata, self.db_session)
        elif parser_name == "team_distance":
            distance_data = self._required_payload(downloaded_data, "distance_covered")
            self._validate_team_distance_references(distance_data)
            parse_and_persist_distance_covered(game, distance_data, self.db_session)
        elif parser_name == "player_distance":
            distance_data = self._required_payload(downloaded_data, "distance_covered")
            team_mapping = self.build_player_to_team_mapping(
                downloaded_data.get("metadata") or {}
            )
            team_mapping = self.resolve_player_team_mapping(
                game,
                distance_data,
                team_mapping,
            )
            parse_and_persist_player_distance_covered(
                game,
                distance_data,
                self.db_session,
                team_mapping=team_mapping,
            )
        elif parser_name == "rgd":
            rgd_data = self._required_payload(downloaded_data, "rgd")
            parse_and_persist_rgd(
                game=game,
                game_name=game.name,
                db_session=self.db_session,
                rgd_json_data=rgd_data,
                clean_existing=True,
                task_id=self.task_id,
                round_name=game.round,
            )
        elif parser_name == "goals":
            parse_and_persist_goals(
                game,
                self._required_payload(downloaded_data, "rgd"),
                self.db_session,
            )
        elif parser_name == "fitness":
            fitness_data = self._required_payload(downloaded_data, "fitness_entities")
            self._validate_fitness_references(fitness_data)
            parse_and_persist_fitness_entities(
                game=game,
                fitness_data=fitness_data,
                db_session=self.db_session,
                calculate_summaries=True,
            )
        else:
            raise ValueError(f"Unsupported parser: {parser_name}")

        self.db_session.commit()

    def validate_selected_parser_combination(
        self,
        game: Game,
        parser_names: List[str],
    ) -> None:
        if "rgd" in parser_names and "fitness" not in parser_names:
            fitness_exists = self.db_session.query(PlayerFitnessRun.id).filter(
                PlayerFitnessRun.game_id == game.id
            ).first()
            if fitness_exists:
                raise ValueError(
                    "Reprocessing RGD would alter existing fitness-run references. "
                    "Select both RGD and Fitness to refresh them together."
                )

    @staticmethod
    def _required_payload(downloaded_data: Dict[str, Any], file_type: str) -> Dict[str, Any]:
        payload = downloaded_data.get(file_type)
        if not isinstance(payload, dict):
            raise ValueError(f"Required {file_type} payload is missing or invalid")
        return payload

    def _validate_substitution_references(
        self,
        game: Game,
        metadata: Dict[str, Any],
    ) -> None:
        metadata_content = metadata.get("metadata", metadata)
        substitutions = metadata_content.get("events", {}).get("substitutions", [])
        missing_players = set()
        missing_teams = set()
        malformed_substitutions = 0
        for substitution in substitutions:
            if not isinstance(substitution, dict):
                continue
            if not all(
                substitution.get(field)
                for field in ("player_in_id", "player_out_id", "team_id")
            ):
                malformed_substitutions += 1
                continue
            for player_id in (
                substitution.get("player_in_id"),
                substitution.get("player_out_id"),
            ):
                if player_id and not self.db_session.query(Player.id).filter(
                    Player.id == player_id
                ).first():
                    missing_players.add(player_id)
            team_id = substitution.get("team_id")
            if team_id and not self.db_session.query(Team.id).filter(
                Team.id == team_id
            ).first():
                missing_teams.add(team_id)

        if malformed_substitutions or missing_players or missing_teams:
            raise ValueError(
                "Substitution parser prerequisites are missing: "
                f"malformed={malformed_substitutions}, "
                f"players={sorted(missing_players)}, teams={sorted(missing_teams)}"
            )

    @staticmethod
    def _validate_lineup_payload(metadata: Dict[str, Any]) -> None:
        metadata_content = metadata.get("metadata", metadata)
        lineups = metadata_content.get("lineups", [])
        for lineup_index, lineup in enumerate(lineups):
            if not isinstance(lineup, dict) or not lineup.get("id"):
                raise ValueError(
                    f"Lineup payload has an incomplete team at index {lineup_index}"
                )
            players = lineup.get("players", [])
            for player_index, player in enumerate(players):
                if not isinstance(player, dict) or not player.get("id"):
                    raise ValueError(
                        "Lineup payload has an incomplete player at "
                        f"{lineup_index}:{player_index}"
                    )

    def _validate_team_distance_references(
        self,
        distance_data: Dict[str, Any],
    ) -> None:
        teams = distance_data.get("teams", [])
        malformed_teams = [
            index
            for index, team in enumerate(teams)
            if not isinstance(team, dict)
            or not team.get("team_id")
            or team.get("total_distance_m") is None
        ]
        if malformed_teams:
            raise ValueError(
                f"Team distance payload has incomplete entries at indexes: {malformed_teams}"
            )
        team_ids = {
            str(team.get("team_id"))[:200]
            for team in teams
            if isinstance(team, dict) and team.get("team_id")
        }
        existing_ids = {
            row[0]
            for row in self.db_session.query(Team.id).filter(Team.id.in_(team_ids)).all()
        } if team_ids else set()
        missing_ids = sorted(team_ids - existing_ids)
        if missing_ids:
            raise ValueError(
                f"Team distance parser requires existing teams: {missing_ids}"
            )

    def resolve_player_team_mapping(
        self,
        game: Game,
        distance_data: Dict[str, Any],
        team_mapping: Dict[str, str],
    ) -> Dict[str, str]:
        player_ids = {
            str(player.get("player_id"))[:200]
            for player in distance_data.get("players", [])
            if isinstance(player, dict) and player.get("player_id")
        }
        existing_player_ids = {
            row[0]
            for row in self.db_session.query(Player.id).filter(
                Player.id.in_(player_ids)
            ).all()
        } if player_ids else set()
        missing_players = sorted(player_ids - existing_player_ids)
        if missing_players:
            raise ValueError(
                f"Player distance parser requires existing players: {missing_players}"
            )
        malformed_players = [
            index
            for index, player in enumerate(distance_data.get("players", []))
            if not isinstance(player, dict)
            or not player.get("player_id")
            or player.get("total_distance_m") is None
        ]
        if malformed_players:
            raise ValueError(
                "Player distance payload has incomplete entries at indexes: "
                f"{malformed_players}"
            )

        unmapped_ids = player_ids - set(team_mapping)
        db_assignments = (
            self.db_session.query(LineupPlayer.player_id, LineupTeam.team_id)
            .join(LineupTeam)
            .filter(
                LineupTeam.game_id == game.id,
                LineupPlayer.player_id.in_(unmapped_ids),
            )
            .all()
            if unmapped_ids
            else []
        )
        for player_id, team_id in db_assignments:
            team_mapping[player_id] = team_id

        missing_team_assignments = sorted(player_ids - set(team_mapping))
        if missing_team_assignments:
            raise ValueError(
                "Player distance parser requires team assignments for players: "
                f"{missing_team_assignments}"
            )

        team_ids = {team_mapping[player_id] for player_id in player_ids}
        existing_team_ids = {
            row[0]
            for row in self.db_session.query(Team.id).filter(Team.id.in_(team_ids)).all()
        } if team_ids else set()
        missing_team_ids = sorted(team_ids - existing_team_ids)
        if missing_team_ids:
            raise ValueError(
                f"Player distance parser requires existing teams: {missing_team_ids}"
            )

        return team_mapping

    def player_distance_needs_metadata(
        self,
        game: Game,
        distance_data: Dict[str, Any],
    ) -> bool:
        player_ids = {
            str(player.get("player_id"))[:200]
            for player in distance_data.get("players", [])
            if isinstance(player, dict) and player.get("player_id")
        }
        if not player_ids:
            return False
        assigned_ids = {
            row[0]
            for row in (
                self.db_session.query(LineupPlayer.player_id)
                .join(LineupTeam)
                .filter(
                    LineupTeam.game_id == game.id,
                    LineupPlayer.player_id.in_(player_ids),
                )
                .all()
            )
        }
        return bool(player_ids - assigned_ids)

    def _validate_fitness_references(self, fitness_data: Dict[str, Any]) -> None:
        entities = fitness_data.get("entities", [])
        persistable_entities = [
            entity for entity in entities if has_fitness_run_references(entity)
        ]
        if entities and not persistable_entities:
            raise ValueError(
                "Fitness payload contains no entities with player, team, "
                "opponent_team, and period_id references"
            )

        player_ids = {entity["player"] for entity in persistable_entities}
        team_ids = {
            team_id
            for entity in persistable_entities
            for team_id in (entity["team"], entity["opponent_team"])
        }
        existing_player_ids = {
            row[0]
            for row in self.db_session.query(Player.id).filter(
                Player.id.in_(player_ids)
            ).all()
        } if player_ids else set()
        existing_team_ids = {
            row[0]
            for row in self.db_session.query(Team.id).filter(
                Team.id.in_(team_ids)
            ).all()
        } if team_ids else set()
        missing_players = sorted(player_ids - existing_player_ids)
        missing_teams = sorted(team_ids - existing_team_ids)
        if missing_players or missing_teams:
            raise ValueError(
                "Fitness parser prerequisites are missing: "
                f"players={missing_players[:20]}, teams={missing_teams}"
            )
