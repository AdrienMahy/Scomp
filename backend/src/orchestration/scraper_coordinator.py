"""ScraperCoordinator - Orchestrates the complete scraping flow"""
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dateutil import parser as date_parser

from ..providers.sportsdynamics_provider import SportsDynamicsProvider
from ..models import Game, Squad, Player, GameStatus, Competition, Season, Team, GameSummary, OutputFile, LineupTeam, LineupPlayer
from ..config.database import SessionLocal

logger = logging.getLogger(__name__)

# Export directory for game JSONs
EXPORT_DIR = Path(__file__).parent.parent.parent / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class ScraperCoordinator:
    """
    Orchestrates the complete scraping flow:
    
    Flow:
    1. Receive filter request
    2. Fetch games from provider (API)
    3. Transform raw JSON to ORM models
    4. Persist to database
    5. Return results
    """
    
    def __init__(self):
        self.provider = SportsDynamicsProvider()
        self.db_session = SessionLocal()
    
    async def scrape_games(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Complete scrape flow for games
        
        Args:
            filters: Filter dictionary with values
            limit: Number of results per page
            page: Page number
            
        Returns:
            List of transformed game dictionaries
        """
        try:
            logger.info(f"Starting scrape_games with filters: {filters}")
            
            # Extract competition and season IDs from filters
            competition_id = filters.get("competition_id")
            season_id = filters.get("season_id")
            
            # 0️⃣ Ensure Competition and Season exist
            self._ensure_competition_exists(competition_id)
            self._ensure_season_exists(season_id, competition_id)
            
            # 1️⃣ Fetch from API
            raw_games = self.provider.fetch_games(filters, limit, page)
            logger.info(f"Got {len(raw_games)} raw games from API")
            
            # 2️⃣ Transform to ORM models
            orm_games = self._transform_to_orm(raw_games, competition_id, season_id)
            logger.info(f"Transformed to {len(orm_games)} ORM models")
            
            # 3️⃣ Persist to database (with raw data for status checking)
            saved_games = self._persist_games(orm_games, raw_games)
            logger.info(f"Persisted {len(saved_games)} games to database")
            
            # 4️⃣ Transform back to dicts for response
            response_games = [self._orm_to_dict(game) for game in saved_games]
            logger.info(f"Transformed {len(response_games)} ORM to dict for response")
            
            logger.info(f"✅ Scrape complete: {len(response_games)} games returned")
            return response_games
            
        except Exception as e:
            logger.error(f"Scrape failed: {e}", exc_info=True)
            raise
        finally:
            self.close()
    
    def _ensure_competition_exists(self, competition_id: str) -> None:
        """
        Ensure Competition record exists, create if not
        
        Args:
            competition_id: SportsDynamics competition ID
        """
        from ..models import Competition
        
        existing = self.db_session.query(Competition).filter(
            Competition.id == competition_id
        ).first()
        
        if not existing:
            logger.info(f"Creating competition record with ID: {competition_id}")
            comp = Competition(
                id=competition_id,
                name=f"Competition {competition_id}",
                provider="SportsDynamics"
            )
            self.db_session.add(comp)
            self.db_session.commit()
    
    def _ensure_season_exists(self, season_id: str, competition_id: str) -> None:
        """
        Ensure Season record exists, create if not
        
        Args:
            season_id: SportsDynamics season ID (typically a year like "2026")
            competition_id: Competition ID this season belongs to
        """
        from ..models import Season
        
        season_id_str = str(season_id)
        existing = self.db_session.query(Season).filter(
            Season.id == season_id_str
        ).first()
        
        if not existing:
            logger.info(f"Creating season record with ID: {season_id_str}")
            # Try to extract season year from season_id
            try:
                season_year = int(season_id_str) if season_id_str.isdigit() else None
            except (ValueError, AttributeError):
                season_year = None
            
            season = Season(
                id=season_id_str,
                name=f"Season {season_id_str}",
                season_year=season_year,
                competition_id=competition_id
            )
            self.db_session.add(season)
            self.db_session.commit()
    
    def _ensure_team_exists(self, team_id: str, team_name: Optional[str] = None) -> None:
        """
        Ensure Team record exists, create if not
        
        Args:
            team_id: SportsDynamics team ID
            team_name: Team name from API response
        """
        from ..models import Team
        
        existing = self.db_session.query(Team).filter(
            Team.id == team_id
        ).first()
        
        if not existing:
            logger.info(f"Creating team record with ID: {team_id}, name: {team_name}")
            team = Team(
                id=team_id,
                name=team_name or f"Team {team_id}"
            )
            self.db_session.add(team)
            self.db_session.commit()
    
    def _calculate_output_files_hash(self, output_files: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of output_files JSON for change detection
        
        Only hashes stable fields (id, fileName, fileType, version, isOutdated)
        Ignores URLs and timestamps which change on every API call
        
        Args:
            output_files: Output files dict from API (with 'items' array)
            
        Returns:
            SHA256 hex hash string
        """
        # Extract stable fields only
        items = output_files.get("items", []) if isinstance(output_files, dict) else []
        
        stable_items = []
        for item in items:
            stable_item = {
                "id": item.get("id"),
                "fileName": item.get("fileName"),
                "fileType": item.get("fileType"),
                "version": item.get("version"),
                "isOutdated": item.get("isOutdated"),
            }
            stable_items.append(stable_item)
        
        # Hash only the stable structure
        stable_data = {"items": stable_items}
        json_str = json.dumps(stable_data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def _should_update_game(self, game_id: str, api_game_data: Dict[str, Any]) -> bool:
        """
        Check if game needs to be updated based on status changes
        
        Returns:
            True = re-download and update everything
            False = skip, data hasn't changed
        """
        # Get current status
        current_status = self.db_session.query(GameStatus).filter(
            GameStatus.game_id == game_id
        ).first()
        
        # No status record → first time downloading
        if not current_status:
            logger.info(f"No status found for game {game_id} - will create")
            return True
        
        # Calculate new hash
        new_output_files = api_game_data.get("outputFiles", [])
        new_hash = self._calculate_output_files_hash(new_output_files)
        
        # Compare fields
        available_changed = current_status.available != api_game_data.get("available", False)
        ugd_available_changed = current_status.is_ugd_available != api_game_data.get("isUGDAvailable", False)
        rgd_status_changed = current_status.rgd_status != api_game_data.get("rgdStatus")
        ugd_status_changed = current_status.ugd_status != api_game_data.get("ugdStatus")
        output_files_changed = current_status.output_files_hash != new_hash
        
        should_update = (
            available_changed or 
            ugd_available_changed or 
            rgd_status_changed or 
            ugd_status_changed or 
            output_files_changed
        )
        
        if should_update:
            logger.info(f"Game {game_id} status changed: "
                       f"available={available_changed}, ugd={ugd_available_changed}, "
                       f"rgd_status={rgd_status_changed}, ugd_status={ugd_status_changed}, "
                       f"output_files={output_files_changed}")
        else:
            logger.info(f"Game {game_id} status unchanged - skipping update")
        
        return should_update
    
    def _delete_game_data(self, game_id: str) -> None:
        """
        Delete all data associated with a game (for clean re-download)
        
        Deletes: Squads, Players, GameStatus
        Game record is kept (FK relationships cascade if needed)
        
        Args:
            game_id: Game ID to delete data for
        """
        try:
            # Delete squads (cascade deletes players via FK)
            squads_deleted = self.db_session.query(Squad).filter(
                Squad.game_id == game_id
            ).delete()
            
            # Delete game status
            status_deleted = self.db_session.query(GameStatus).filter(
                GameStatus.game_id == game_id
            ).delete()
            
            self.db_session.commit()
            logger.info(f"Deleted {squads_deleted} squads and {status_deleted} status records for game {game_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete game data for {game_id}: {e}")
            self.db_session.rollback()
            raise
    
    def _calculate_team_result(self, game_result: str, team_side: str) -> str:
        """
        Calculate result relative to a specific team
        
        Args:
            game_result: "HOME_TEAM_WIN", "AWAY_TEAM_WIN", "DRAW"
            team_side: "HOME" or "AWAY"
            
        Returns:
            "WIN", "LOSS", or "DRAW"
        """
        if game_result == "DRAW":
            return "DRAW"
        
        if team_side == "HOME":
            return "WIN" if game_result == "HOME_TEAM_WIN" else "LOSS"
        else:  # AWAY
            return "WIN" if game_result == "AWAY_TEAM_WIN" else "LOSS"
    
    def _build_teams_structure(self, 
                               game: Game,
                               raw_game: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build denormalized teams array for GameSummary
        
        Args:
            game: Game ORM instance
            raw_game: Raw API response dict (for team names)
            
        Returns:
            List of team dicts with structure:
            [
              {
                "brand": "Nantes",
                "id": "f32406d3-...",
                "side": "HOME",
                "goal": 0,
                "goalconceded": 1,
                "result": "LOSS"
              },
              ...
            ]
        """
        teams_data = []
        
        # Extract names from raw API data (more reliable than DB)
        home_team_name = raw_game.get("homeTeam", {}).get("brand", "Unknown")
        away_team_name = raw_game.get("awayTeam", {}).get("brand", "Unknown")
        
        # Home team
        if game.home_team_id:
            home_team = {
                "brand": home_team_name,
                "id": game.home_team_id,
                "side": "HOME",
                "goal": game.home_score or 0,
                "goalconceded": game.away_score or 0,
                "result": self._calculate_team_result(game.result, "HOME") if game.result else None
            }
            teams_data.append(home_team)
        
        # Away team
        if game.away_team_id:
            away_team = {
                "brand": away_team_name,
                "id": game.away_team_id,
                "side": "AWAY",
                "goal": game.away_score or 0,
                "goalconceded": game.home_score or 0,
                "result": self._calculate_team_result(game.result, "AWAY") if game.result else None
            }
            teams_data.append(away_team)
        
        return teams_data
    
    def _upsert_game_summary(self, 
                            game: Game,
                            raw_game: Dict[str, Any],
                            available: bool = True) -> None:
        """
        Create or update GameSummary record
        
        Args:
            game: Game ORM instance
            raw_game: Raw API response dict
            available: Is this game properly processed?
        """
        try:
            # Build teams structure
            teams = self._build_teams_structure(game, raw_game)
            
            # Check if summary exists
            existing = self.db_session.query(GameSummary).filter(
                GameSummary.game_id == game.id
            ).first()
            
            if existing:
                # Update existing
                existing.name = game.name
                existing.result = game.result
                existing.round = game.round_name
                existing.starts_at = game.starts_at
                existing.played_at = game.played_at
                existing.available = available
                existing.teams = teams
                existing.updated_at = datetime.utcnow()
            else:
                # Create new
                summary = GameSummary(
                    game_id=game.id,
                    name=game.name,
                    result=game.result,
                    round=game.round_name,
                    starts_at=game.starts_at,
                    played_at=game.played_at,
                    available=available,
                    teams=teams
                )
                self.db_session.add(summary)
            
            logger.info(f"💾 Upserted GameSummary for {game.id}, available={available}")
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to upsert GameSummary for {game.id}: {e}")
            # Don't fail the whole process
    
    def _transform_to_orm(
        self, 
        raw_games: List[Dict[str, Any]],
        competition_id: str,
        season_id: str
    ) -> List[Game]:
        """
        Transform raw API response to ORM models
        
        Args:
            raw_games: List of game dicts from API
            competition_id: Competition ID from request
            season_id: Season ID from request
            
        Returns:
            List of Game ORM instances
        """
        games = []
        
        def parse_iso_datetime(dt_string: Optional[str]) -> Optional[datetime]:
            """Parse ISO datetime string to datetime object"""
            if not dt_string:
                return None
            try:
                # Handle ISO 8601 format with Z timezone indicator
                if isinstance(dt_string, str):
                    # Remove 'Z' suffix if present and parse
                    dt_str = dt_string.replace('Z', '+00:00') if dt_string.endswith('Z') else dt_string
                    return date_parser.isoparse(dt_str)
                return dt_string  # Already a datetime object
            except Exception as e:
                logger.warning(f"Failed to parse datetime '{dt_string}': {e}")
                return None
        
        for raw in raw_games:
            try:
                # Ensure teams exist before creating game
                home_team_id = raw.get("homeTeam", {}).get("id")
                away_team_id = raw.get("awayTeam", {}).get("id")
                home_team_name = raw.get("homeTeam", {}).get("name")
                away_team_name = raw.get("awayTeam", {}).get("name")
                
                if home_team_id:
                    self._ensure_team_exists(home_team_id, home_team_name)
                if away_team_id:
                    self._ensure_team_exists(away_team_id, away_team_name)
                
                game = Game(
                    id=raw.get("id"),
                    competition_id=competition_id,
                    season_id=season_id,
                    name=raw.get("name"),
                    result=raw.get("result"),
                    home_score=raw.get("homeScore"),
                    away_score=raw.get("awayScore"),
                    home_team_formation=raw.get("homeTeamFormation"),
                    away_team_formation=raw.get("awayTeamFormation"),
                    starts_at=parse_iso_datetime(raw.get("startsAt")),
                    played_at=parse_iso_datetime(raw.get("playedAt")),
                    round_name=raw.get("round", {}).get("name"),
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    raw_data=raw  # Store complete JSON for reference
                )
                games.append(game)
                
            except Exception as e:
                logger.warning(f"Failed to transform game {raw.get('id')}: {e}")
                continue
        
        return games
    
    def _persist_games(self, orm_games: List[Game], raw_games: List[Dict[str, Any]]) -> List[Game]:
        """
        Persist games to database with incremental update logic
        
        For each game:
        1. Check if status changed (using _should_update_game)
        2. If changed: delete old data and re-persist everything
        3. If not changed: skip (skip row)
        4. Create/update GameStatus record to track current state
        
        Args:
            orm_games: List of Game ORM instances
            raw_games: List of raw API response dicts (for status checking)
            
        Returns:
            List of persisted Game instances
        """
        logger.info(f"💾 Persisting {len(orm_games)} games with incremental logic...")
        saved_games = []
        output_files_to_persist = {}  # Map of game_id -> output_files_data
        lineups_to_persist = {}  # Map of game_id -> squads_data
        
        # Create a map of game_id -> raw_game_data for lookup
        raw_games_map = {game.get("id"): game for game in raw_games}
        
        for game in orm_games:
            try:
                raw_data = raw_games_map.get(game.id)
                if not raw_data:
                    logger.warning(f"No raw data found for game {game.id} - skipping")
                    continue
                
                # 📊 Check if game needs update
                if not self._should_update_game(game.id, raw_data):
                    logger.info(f"⏭️  Skipping game {game.id} - status unchanged")
                    # Still need to return it for API response
                    existing = self.db_session.query(Game).filter(Game.id == game.id).first()
                    if existing:
                        saved_games.append(existing)
                    continue
                
                # 🗑️ Delete old data if game exists
                existing = self.db_session.query(Game).filter(Game.id == game.id).first()
                if existing:
                    logger.info(f"🗑️  Deleting old data for game {game.id} (status changed)")
                    self._delete_game_data(game.id)
                    # Update existing game record
                    for key, value in game.__dict__.items():
                        if not key.startswith('_') and key != 'id':
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    self.db_session.add(existing)
                else:
                    # Create new game
                    logger.info(f"✨ Creating new game {game.id}")
                    self.db_session.add(game)
                
                saved_games.append(game)
                
                # 📌 Create/update GameStatus record
                output_files_data = raw_data.get("outputFiles", {})
                output_files_list = output_files_data.get("items", []) if isinstance(output_files_data, dict) else output_files_data
                output_files_hash = self._calculate_output_files_hash(output_files_list)
                
                status = self.db_session.query(GameStatus).filter(
                    GameStatus.game_id == game.id
                ).first()
                
                if status:
                    status.available = raw_data.get("available", False)
                    status.is_ugd_available = raw_data.get("isUGDAvailable", False)
                    status.rgd_status = raw_data.get("rgdStatus")
                    status.ugd_status = raw_data.get("ugdStatus")
                    status.output_files = output_files_list
                    status.output_files_hash = output_files_hash
                    status.last_checked_at = datetime.utcnow()
                    status.status_changed_at = datetime.utcnow()
                else:
                    status = GameStatus(
                        game_id=game.id,
                        available=raw_data.get("available", False),
                        is_ugd_available=raw_data.get("isUGDAvailable", False),
                        rgd_status=raw_data.get("rgdStatus"),
                        ugd_status=raw_data.get("ugdStatus"),
                        output_files=output_files_list,
                        output_files_hash=output_files_hash,
                        last_checked_at=datetime.utcnow(),
                        status_changed_at=datetime.utcnow()
                    )
                
                self.db_session.add(status)
                
                # 📁 Save output files data for later (after commit to avoid autoflush)
                output_files_to_persist[game.id] = output_files_data
                
                # 👥 Save squads/lineups data for later
                lineups_to_persist[game.id] = raw_data.get("squads", [])
                
            except Exception as e:
                logger.warning(f"❌ Failed to persist game {game.id}: {e}", exc_info=True)
                continue
        
        # Commit all changes
        try:
            logger.info(f"💾 Committing {len(saved_games)} games to database...")
            self.db_session.commit()
            logger.info(f"✅ Committed {len(saved_games)} games to database")
        except Exception as e:
            logger.error(f"❌ Database commit failed: {e}", exc_info=True)
            self.db_session.rollback()
            raise
        
        # 📁 Persist output files AFTER commit
        logger.info(f"📁 About to persist output files for {len(output_files_to_persist)} games")
        for game_id, output_files_data in output_files_to_persist.items():
            try:
                self._persist_output_files(game_id, output_files_data)
            except Exception as e:
                logger.warning(f"❌ Failed to persist output files for {game_id}: {e}", exc_info=True)
                continue
        
        # Commit OutputFile records
        if output_files_to_persist:
            try:
                logger.info(f"💾 Committing {len(output_files_to_persist)} output file batches to database...")
                self.db_session.commit()
                logger.info(f"✅ Committed output files to database")
            except Exception as e:
                logger.error(f"❌ Output files commit failed: {e}", exc_info=True)
                self.db_session.rollback()
                raise
        
        # 👥 Persist lineups AFTER output files
        logger.info(f"👥 About to persist lineups for {len(lineups_to_persist)} games")
        for game_id, squads_data in lineups_to_persist.items():
            try:
                self._persist_lineups(game_id, squads_data)
            except Exception as e:
                logger.warning(f"❌ Failed to persist lineups for {game_id}: {e}", exc_info=True)
                continue
        
        # Commit LineupTeam/LineupPlayer records
        if lineups_to_persist:
            try:
                logger.info(f"💾 Committing lineups to database...")
                self.db_session.commit()
                logger.info(f"✅ Committed lineups to database")
            except Exception as e:
                logger.error(f"❌ Lineups commit failed: {e}", exc_info=True)
                self.db_session.rollback()
                raise
        
        # 📊 Upsert GameSummary records for each game
        for game in saved_games:
            try:
                raw_data = raw_games_map.get(game.id)
                if raw_data:
                    # available = True if game was successfully processed
                    self._upsert_game_summary(game, raw_data, available=True)
            except Exception as e:
                logger.warning(f"⚠️  Failed to upsert summary for {game.id}: {e}")
                continue
        
        # Final commit for GameSummary
        try:
            self.db_session.commit()
            logger.info(f"✅ Committed GameSummary records")
        except Exception as e:
            logger.error(f"❌ GameSummary commit failed: {e}", exc_info=True)
            self.db_session.rollback()
        
        # 📦 Export each game to JSON
        for game in saved_games:
            try:
                self._export_game_to_json(game)
            except Exception as e:
                logger.warning(f"⚠️  Failed to export game {game.id} to JSON: {e}")
                # Don't fail the whole process if export fails
                continue
        
        return saved_games
    
    def _orm_to_dict(self, game: Game) -> Dict[str, Any]:
        """
        Convert ORM Game model to dictionary for API response
        
        Args:
            game: Game ORM instance
            
        Returns:
            Dictionary representation of the game
        """
        try:
            result = {
                "id": game.id,
                "name": game.name,
                "result": game.result,
                "home_score": game.home_score,
                "away_score": game.away_score,
                "starts_at": game.starts_at.isoformat() if game.starts_at else None,
                "played_at": game.played_at.isoformat() if game.played_at else None,
                "round_name": game.round_name,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "home_team_formation": game.home_team_formation,
                "away_team_formation": game.away_team_formation,
                "created_at": game.created_at.isoformat() if game.created_at else None,
                "updated_at": game.updated_at.isoformat() if game.updated_at else None,
            }
            return result
        except Exception as e:
            logger.error(f"❌ Failed to convert game {game.id} to dict: {e}")
            raise
    
    def _export_game_to_json(self, game: Game) -> None:
        """
        Export a single game to JSON file with complete raw API response
        
        Args:
            game: Game ORM instance to export
            
        Returns:
            None
        """
        try:
            # Export the complete raw response from GraphQL API
            export_data = game.raw_data
            
            # Create filename with format: [Round]_[GameName]
            round_name = game.round_name or "unknown"
            safe_name = game.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            filename = f"{round_name}_{safe_name}.json"
            filepath = EXPORT_DIR / filename
            
            # Write JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"📦 Exported game {game.id} to {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Failed to export game {game.id} to JSON: {e}", exc_info=True)
            raise
    
    def _persist_output_files(self, game_id: str, output_files_data: Dict[str, Any]) -> None:
        """
        Save individual output files to OutputFile table
        
        Replaces storing full array in GameStatus
        Allows querying files by type, status, etc.
        
        Args:
            game_id: Game ID
            output_files_data: outputFiles dict from API (structure: {"items": [...]})
        """
        try:
            # Extract items array from outputFiles structure
            output_files = output_files_data.get("items", [])
            if not output_files:
                logger.info(f"ℹ️  No output files for game {game_id}")
                return
            
            # Delete existing output files for this game
            deleted_count = self.db_session.query(OutputFile).filter(
                OutputFile.game_id == game_id
            ).delete()
            if deleted_count > 0:
                logger.info(f"🗑️  Deleted {deleted_count} old output files for {game_id}")
            
            # Save each file
            for file_item in output_files:
                file_info = file_item.get("file", {})
                
                output_file = OutputFile(
                    id=file_item.get("id"),
                    game_id=game_id,
                    file_name=file_item.get("fileName", ""),
                    file_type=file_item.get("fileType", ""),
                    version=file_item.get("version"),
                    is_outdated=file_item.get("isOutdated", False),
                    url=file_info.get("url"),
                    file_size=file_info.get("size"),
                    file_name_raw=file_info.get("name"),
                    available=True
                )
                self.db_session.add(output_file)
            
            logger.info(f"✅ Persisted {len(output_files)} output files for game {game_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to persist output files for {game_id}: {e}", exc_info=True)
            raise
    
    def _persist_lineups(self, game_id: str, squads_data: List[Dict[str, Any]]) -> None:
        """
        Save player lineups to LineupTeam and LineupPlayer tables
        
        Deduplicates players by ID and tracks their participation in each game
        
        Args:
            game_id: Game ID
            squads_data: List of squad dicts from API (structure: [{"teamId": "...", "players": {...}}])
        """
        try:
            if not squads_data:
                logger.info(f"ℹ️  No squads data for game {game_id}")
                return
            
            # Delete existing lineups for this game
            deleted_lineups = self.db_session.query(LineupTeam).filter(
                LineupTeam.game_id == game_id
            ).delete()
            if deleted_lineups > 0:
                logger.info(f"🗑️  Deleted {deleted_lineups} old lineups for {game_id}")
            
            # Commit the delete first
            self.db_session.commit()
            
            # Determine HOME/AWAY position
            game = self.db_session.query(Game).filter(Game.id == game_id).first()
            if not game:
                logger.warning(f"Game {game_id} not found when persisting lineups")
                return
            
            # Process each squad (HOME and AWAY)
            positions = ["HOME", "AWAY"]
            for idx, squad_data in enumerate(squads_data):
                if idx >= len(positions):
                    logger.warning(f"More than 2 squads for game {game_id}, skipping squad {idx}")
                    continue
                
                team_id = squad_data.get("teamId")
                players_data = squad_data.get("players", {})
                
                if not team_id:
                    logger.warning(f"No teamId in squad data for game {game_id}")
                    continue
                
                # Create LineupTeam record
                lineup_team = LineupTeam(
                    id=f"{game_id}_{team_id}_{positions[idx]}",
                    game_id=game_id,
                    team_id=team_id,
                    position=positions[idx]
                )
                self.db_session.add(lineup_team)
                
                # Get players from the squad
                players_items = players_data.get("items", []) if isinstance(players_data, dict) else []
                
                # Collect all player IDs in this squad
                player_ids_in_squad = [p.get("player", {}).get("id") for p in players_items if p.get("player", {}).get("id")]
                
                # Pre-fetch existing players to avoid duplicate attempts
                existing_players = {}
                if player_ids_in_squad:
                    existing_players_list = self.db_session.query(Player).filter(
                        Player.id.in_(player_ids_in_squad)
                    ).all()
                    existing_players = {p.id: p for p in existing_players_list}
                
                # Process each player
                players_to_add = []
                for player_data in players_items:
                    player_info = player_data.get("player", {})
                    player_id = player_info.get("id")
                    
                    if not player_id:
                        logger.warning(f"No player ID in squad data for game {game_id}")
                        continue
                    
                    # Get or create Player record
                    if player_id not in existing_players:
                        player = Player(
                            id=player_id,
                            first_name=player_info.get("firstName"),
                            last_name=player_info.get("lastName"),
                            name=player_info.get("name", player_info.get("usageName", "")),
                            usage_name=player_info.get("usageName")
                        )
                        players_to_add.append(player)
                        existing_players[player_id] = player
                    else:
                        player = existing_players[player_id]
                        # Update player info if needed
                        if player_info.get("firstName"):
                            player.first_name = player_info.get("firstName")
                        if player_info.get("lastName"):
                            player.last_name = player_info.get("lastName")
                        if player_info.get("name"):
                            player.name = player_info.get("name")
                        if player_info.get("usageName"):
                            player.usage_name = player_info.get("usageName")
                        player.updated_at = datetime.utcnow()
                
                # Add all new players to session (one by one to avoid bulk insert issues)
                for player in players_to_add:
                    try:
                        self.db_session.add(player)
                        self.db_session.flush()  # Flush to catch constraint violations early
                    except Exception as e:
                        logger.warning(f"Player {player.id} already exists, skipping duplicate: {e}")
                        self.db_session.rollback()  # Rollback this player's add
                        # Continue with next player
                        continue
                
                # Create LineupPlayer records for all players
                for player_data in players_items:
                    player_info = player_data.get("player", {})
                    player_id = player_info.get("id")
                    
                    if not player_id:
                        continue
                    
                    # Get the player from existing_players
                    if player_id not in existing_players:
                        logger.warning(f"Player {player_id} not found after persist attempt")
                        continue
                    
                    player = existing_players[player_id]
                    
                    # Create LineupPlayer record (ID auto-generated)
                    lineup_player = LineupPlayer(
                        lineup_team_id=f"{game_id}_{team_id}_{positions[idx]}",
                        player_id=player_id,
                        is_starting=player_data.get("isStarting", False),
                        is_captain=player_data.get("isCaptain", False),
                        formation_field=player_data.get("formationField"),
                        formation_position=player_data.get("formationPosition"),
                        jersey_number=player_data.get("jerseyNumber"),
                        playing_time=player_data.get("playingTime")
                    )
                    self.db_session.add(lineup_player)
                
                logger.info(f"✅ Persisted {len(players_items)} players for {positions[idx]} lineup in game {game_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to persist lineups for {game_id}: {e}", exc_info=True)
            raise
    
    def close(self):
        """Close database session"""
        if self.db_session:
            self.db_session.close()

