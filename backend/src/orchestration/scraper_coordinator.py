"""ScraperCoordinator - Orchestrates the complete scraping flow"""
import json
import logging
import hashlib
from typing import Callable, Dict, Any, List, Optional
from datetime import datetime
from dateutil import parser as date_parser
import time
import urllib.request
from urllib.error import URLError, HTTPError
from io import BytesIO

from ..providers.sportsdynamics_provider import SportsDynamicsProvider
from ..models import (
    Game, Player, GameStatus, Competition, Season, Team, OutputFile,
    LineupTeam, LineupPlayer, Period, GameScoreEvolution, Events,
    BallInPlay, Card, Foul, GoalKick, Goals, IndividualPossession,
    Kickoff, Offside, PhaseOfPlay, PossessionCollective, Setpieces,
    TypeOfPlay,
    GameSubstitution, PlayerDistanceCovered, TeamDistanceCovered,
    PlayerFitnessRun, PlayerFitnessSummary, TeamFitnessSummary
)
from ..config.database import SessionLocal
from .metadata_parser import (
    parse_and_persist_lineups,
    parse_and_persist_periods,
)
from .substitutions_parser import parse_and_persist_substitutions
from .player_distance_covered_parser import parse_and_persist_player_distance_covered
from .distance_covered_parser import parse_and_persist_distance_covered
from .fitness_entities_parser import parse_and_persist_fitness_entities
from .rgd_parser import parse_and_persist_rgd, _log_to_db

logger = logging.getLogger(__name__)

def log_phase(phase_num: int, phase_name: str) -> None:
    """Log the start of a new scrape phase"""
    logger.info(f"\n[PHASE {phase_num}] 🔄 {phase_name}")


def log_phase_complete(phase_time: float) -> None:
    """Log completion of a phase with timing"""
    logger.info(f"✅ Complete ({phase_time:.2f}s)")


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
    
    def __init__(self, task_id: Optional[str] = None):
        self.provider = SportsDynamicsProvider()
        self.db_session = SessionLocal()
        self.task_id = task_id  # For logging to DB
        self.request_timestamp = datetime.utcnow()
    
    async def scrape_games(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        page: int = 1,
        game_id_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Complete scrape flow for games
        
        Args:
            filters: Filter dictionary with values
            limit: Number of results per page
            page: Page number
            game_id_filter: Optional game ID to persist only that game (useful for force-scrape)
            
        Returns:
            List of transformed game dictionaries
        """
        scrape_start = time.time()
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"🚀 [PHASE 0] Starting scrape_games")
            logger.info(f"   Filters: {filters}")
            logger.info(f"   Time: {datetime.now().isoformat()}")
            if game_id_filter:
                logger.info(f"📌 Filter mode: Only persisting game {game_id_filter}")
            
            # Extract competition and season IDs from filters
            competition_id = filters.get("competition_id")
            season_id = filters.get("season_id")
            season_name = filters.get("season_name")
            
            # 0️⃣ Ensure Competition and Season exist
            self._ensure_competition_exists(competition_id)
            self._ensure_season_exists(season_id, competition_id, season_name)
            
            # 1️⃣ Fetch from API
            raw_games = self.provider.fetch_games(filters, limit, page)
            logger.info(f"Got {len(raw_games)} raw games from API")
            
            # 📊 Log structure of first game to check if outputFiles are present
            if raw_games:
                first_game = raw_games[0]
                logger.info(f"   🔍 First game keys: {list(first_game.keys())}")
                if "outputFiles" in first_game:
                    logger.info(f"   ✅ outputFiles found in game: {type(first_game['outputFiles'])}")
                    if isinstance(first_game["outputFiles"], dict):
                        logger.info(f"      outputFiles keys: {list(first_game['outputFiles'].keys())}")
                        if "items" in first_game["outputFiles"]:
                            logger.info(f"      items count: {len(first_game['outputFiles']['items'])}")
                else:
                    logger.warning(f"   ⚠️  outputFiles NOT found in game data")
            
            # 2️⃣ Transform to ORM models
            orm_games = self._transform_to_orm(raw_games, competition_id, season_id)
            logger.info(f"Transformed to {len(orm_games)} ORM models")
            
            # 2.5️⃣ Filter ORM games if game_id_filter is specified
            if game_id_filter:
                logger.info(f"\n[PHASE 3.5] Filtering for single game")
                orm_games_filtered = [g for g in orm_games if g.id == game_id_filter]
                if orm_games_filtered:
                    logger.info(f"✅ Filtered to 1 game: {game_id_filter}")
                    orm_games = orm_games_filtered
                else:
                    logger.warning(f"❌ Game {game_id_filter} not found in scraped results")
            
            # 3️⃣ Persist to database (with raw data for status checking)
            logger.info(f"\n[PHASE 4] Persisting to database")
            phase4_start = time.time()
            saved_games = self._persist_games(orm_games, raw_games)
            phase4_time = time.time() - phase4_start
            logger.info(f"✅ Persisted {len(saved_games)} games to database ({phase4_time:.2f}s)")
            
            # 3.5️⃣ Create default periods for games without them
            logger.info(f"\n[PHASE 4.5] Creating default periods")
            self._create_default_periods_for_games(saved_games)
            
            # 4️⃣ Transform back to dicts for response
            logger.info(f"\n[PHASE 5] Transforming to response format")
            phase5_start = time.time()
            response_games = [self._orm_to_dict(game) for game in saved_games]
            phase5_time = time.time() - phase5_start
            logger.info(f"✅ Transformed {len(response_games)} ORM to dict ({phase5_time:.2f}s)")
            
            total_time = time.time() - scrape_start
            logger.info(f"\n✅ [COMPLETE] Scrape finished: {len(response_games)} games returned")
            logger.info(f"   Total time: {total_time:.2f}s")
            logger.info(f"{'='*80}\n")
            return response_games
            
        except Exception as e:
            total_time = time.time() - scrape_start
            logger.error(f"\n❌ [ERROR] Scrape failed after {total_time:.2f}s: {e}", exc_info=True)
            logger.error(f"{'='*80}\n")
            raise
        finally:
            self.close()
    
    async def scrape_games_basic(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Scrape ONLY basic game information (calendrier/schedule)
        
        Does NOT download the 4 JSON files (metadata, distance, fitness, rgd).
        Perfect for season initialization to get the match calendar quickly.
        
        Args:
            filters: Filter dictionary with values
            limit: Number of results per page
            page: Page number
            
        Returns:
            List of transformed game dictionaries (basic info only)
        """
        try:
            logger.info(f"Starting scrape_games_basic (schedule only) with filters: {filters}")
            
            # Extract competition and season IDs from filters
            competition_id = filters.get("competition_id")
            season_id = filters.get("season_id")
            season_name = filters.get("season_name")
            
            # 0️⃣ Ensure Competition and Season exist
            self._ensure_competition_exists(competition_id)
            self._ensure_season_exists(season_id, competition_id, season_name)
            
            # 1️⃣ Fetch from API
            raw_games = self.provider.fetch_games(filters, limit, page)
            logger.info(f"Got {len(raw_games)} raw games from API")
            
            # 2️⃣ Transform to ORM models
            orm_games = self._transform_to_orm(raw_games, competition_id, season_id)
            logger.info(f"Transformed to {len(orm_games)} ORM models")
            
            # 3️⃣ Persist ONLY Games + Teams + GameStatus (NO JSON files)
            saved_games = self._persist_games_basic(orm_games, raw_games)
            logger.info(f"Persisted {len(saved_games)} games to database (schedule only)")
            
            # 4️⃣ Transform back to dicts for response
            response_games = [self._orm_to_dict(game) for game in saved_games]
            logger.info(f"Transformed {len(response_games)} ORM to dict for response")
            
            logger.info(f"✅ Basic scrape complete: {len(response_games)} games returned")
            return response_games
            
        except Exception as e:
            logger.error(f"Basic scrape failed: {e}", exc_info=True)
            raise
        finally:
            self.close()
    
    async def scrape_available_files(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        page: int = 1,
        progress_callback: Optional[Callable[[int, int, int, Optional[str]], None]] = None,
        cancellation_callback: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Scrape available JSON files for games that have them (WEEK/Weekly scrape)
        
        Fetches games matching the filters, then:
        1. Filters for available=true games only
        2. Downloads JSON files (metadata, distance_covered, fitness_entities, rgd)
        3. Parses and injects data into database
        
        Perfect for weekly processing of available match data.
        
        Args:
            filters: Filter dictionary with values
            limit: Number of results per page
            page: Page number
            progress_callback: Callback receiving processed, failed, skipped,
                and current game ID after each game attempt.
            cancellation_callback: Callback checked before each game.
            
        Returns:
            Dict with scrape summary: total_games, processed_count, skipped_count, errors
        """
        scrape_start = time.time()
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"🌟 [WEEKLY SCRAPE] Starting scrape_available_files")
            logger.info(f"   Filters: {filters}")
            logger.info(f"   Time: {datetime.now().isoformat()}")
            
            # Extract competition and season IDs from filters
            competition_id = filters.get("competition_id")
            season_id = filters.get("season_id")
            
            # 1️⃣ Fetch all games from API
            logger.info(f"\n[PHASE 1] Fetching games from API")
            phase1_start = time.time()
            raw_games = self.provider.fetch_games(filters, limit, page)
            phase1_time = time.time() - phase1_start
            logger.info(f"📥 Got {len(raw_games)} raw games from API ({phase1_time:.2f}s)")
            
            # 2️⃣ Process ALL games (not just those marked available)
            # The API might return available=false even if data exists
            # We'll attempt to download JSONs and gracefully handle missing files
            logger.info(f"📦 Will process all {len(raw_games)} games (available field: {[g.get('available') for g in raw_games[:3]]}...)")
            
            if not raw_games:
                logger.warning(f"⚠️  No games found for this season")
                logger.info(f"{'='*80}\n")
                return {
                    "total_games": 0,
                    "processed_count": 0,
                    "skipped_count": 0,
                    "error_count": 0,
                    "message": "No games found for this season"
                }
            
            # 3️⃣ Transform to ORM models
            logger.info(f"\n[PHASE 2] Transforming to ORM models")
            phase2_start = time.time()
            orm_games = self._transform_to_orm(raw_games, competition_id, season_id)
            phase2_time = time.time() - phase2_start
            logger.info(f"✅ Transformed to {len(orm_games)} ORM models ({phase2_time:.2f}s)")
            
            # 4️⃣ Download and process files for each game
            logger.info(f"\n[PHASE 3] Processing JSON files for each game")
            phase3_start = time.time()
            processed_count = 0
            error_count = 0
            skipped_count = 0
            
            for idx, (orm_game, raw_game) in enumerate(zip(orm_games, raw_games)):
                if cancellation_callback and cancellation_callback():
                    logger.info("Scrape cancellation requested; stopping before next game")
                    return {
                        "total_games": len(raw_games),
                        "available_games": processed_count,
                        "processed_count": processed_count,
                        "skipped_count": skipped_count,
                        "error_count": error_count,
                        "cancelled": True,
                        "message": "Scrape cancelled",
                    }
                game_start = time.time()
                try:
                    logger.info(f"\n  [{idx+1}/{len(orm_games)}] 📦 {orm_game.name}")
                    
                    # Get output files from API response
                    output_files_data = raw_game.get("outputFiles", {"items": []})
                    
                    if not output_files_data.get("items"):
                        logger.warning(f"     ⏭️  Skip (no output files)")
                        skipped_count += 1
                        if progress_callback:
                            progress_callback(processed_count, error_count, skipped_count, orm_game.id)
                        continue
                    
                    # Persist the game if it doesn't exist (or use existing one)
                    existing_game = self.db_session.query(Game).filter(Game.id == orm_game.id).first()
                    if not existing_game:
                        self.db_session.add(orm_game)
                        self.db_session.flush()
                        logger.info(f"     ➕ New game")
                        game_to_process = orm_game
                    else:
                        # Use existing game from session (so updates are tracked)
                        game_to_process = existing_game
                        logger.info(f"     ♻️  Reprocessing existing")
                    
                    # Persist output files metadata to DB
                    logger.info(f"     📄 Processing JSON files...")
                    self._persist_output_files(game_to_process.id, output_files_data)
                    
                    # Download and process JSON files (in-memory, no disk I/O)
                    logger.info(f"     📥 Downloading JSON files...")
                    downloaded_data = self._download_json_output_files(game_to_process.id, game_to_process.name, output_files_data)
                    
                    # Process each file type with timing (pass data directly, no disk reads)
                    etl_start = time.time()
                    
                    if "metadata" in downloaded_data:
                        self._process_metadata_json(game_to_process, downloaded_data["metadata"])
                        logger.info(f"       ✓ Metadata")
                    
                    if "rgd" in downloaded_data:
                        self._process_rgd_json(
                            game_to_process,
                            game_to_process.name,
                            downloaded_data["rgd"],
                        )
                        logger.info(f"       ✓ RGD events")

                    if "distance_covered" in downloaded_data:
                        self._process_distance_covered_json(game_to_process, downloaded_data["distance_covered"], downloaded_data.get("metadata"))
                        logger.info(f"       ✓ Distance covered")

                    if "fitness_entities" in downloaded_data:
                        self._process_fitness_entities_json(game_to_process, downloaded_data["fitness_entities"])
                        logger.info(f"       ✓ Fitness entities")
                    
                    # Mark game as processed (data downloaded & injected into DB)
                    game_to_process.data_processed = True

                    # A successful local parse is the authoritative local
                    # availability state, even when SportsDynamics returned
                    # available=false during the initial schedule fetch.
                    output_files = output_files_data.get("items", [])
                    game_status = self.db_session.query(GameStatus).filter(
                        GameStatus.game_id == game_to_process.id
                    ).first()
                    if game_status is None:
                        game_status = GameStatus(game_id=game_to_process.id)
                        self.db_session.add(game_status)
                    game_status.available = True
                    game_status.is_ugd_available = True
                    game_status.rgd_status = raw_game.get("rgdStatus") or "FINISHED"
                    game_status.ugd_status = raw_game.get("ugdStatus") or "FINISHED"
                    game_status.output_files = output_files
                    game_status.output_files_hash = self._calculate_output_files_hash(output_files)
                    game_status.last_checked_at = datetime.utcnow()
                    game_status.status_changed_at = datetime.utcnow()
                    
                    # Commit after each successful game
                    self.db_session.commit()
                    self._log_game_insert_stats(game_to_process)
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, error_count, skipped_count, game_to_process.id)
                    game_time = time.time() - game_start
                    logger.info(f"     ✅ Complete ({game_time:.1f}s)")
                    
                except Exception as e:
                    error_count += 1
                    game_time = time.time() - game_start
                    logger.error(f"     ❌ Error ({game_time:.1f}s): {e}")
                    self.db_session.rollback()
                    if progress_callback:
                        progress_callback(processed_count, error_count, skipped_count, orm_game.id)
                    continue
            
            phase3_time = time.time() - phase3_start
            logger.info(f"\n[PHASE 3 COMPLETE] JSON processing finished ({phase3_time:.1f}s)")
            logger.info(f"\n🎉 Weekly scrape summary:")
            logger.info(f"  • Total games:    {len(raw_games)}")
            logger.info(f"  • Processed:      {processed_count}")
            logger.info(f"  • Skipped:        {skipped_count}")
            logger.info(f"  • Errors:         {error_count}")
            
            total_time = time.time() - scrape_start
            logger.info(f"\n✅ [COMPLETE] Weekly scrape finished in {total_time:.1f}s")
            logger.info(f"{'='*80}\n")
            
            return {
                "total_games": len(raw_games),
                "available_games": processed_count,  # For compatibility
                "processed_count": processed_count,
                "skipped_count": skipped_count,
                "error_count": error_count,
                "message": f"Processed {processed_count} games ({error_count} errors, {skipped_count} skipped)",
                "export_file": f"request_{self.request_timestamp.strftime('%Y%m%d_%H%M%S')}.json" if self.request_timestamp else None,
                "total_time_seconds": total_time
            }
            
        except Exception as e:
            total_time = time.time() - scrape_start
            logger.error(f"\n❌ [ERROR] Weekly scrape failed after {total_time:.1f}s: {e}", exc_info=True)
            logger.error(f"{'='*80}\n")
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
    
    def _ensure_season_exists(self, season_id: str, competition_id: str, season_name: Optional[str] = None) -> None:
        """
        Ensure Season record exists, create if not
        
        Args:
            season_id: SportsDynamics season ID (typically a year like "2026")
            competition_id: Competition ID this season belongs to
            season_name: Full season name (e.g. "2026 - 2027")
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
            
            # Use provided season_name or fall back to ID-based name
            season_display_name = season_name if season_name else f"Season {season_id_str}"
            
            season = Season(
                id=season_id_str,
                name=season_display_name,
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
        # Accept either the full dict {"items": [...]} or a plain list of items
        if isinstance(output_files, dict):
            items = output_files.get("items", [])
        elif isinstance(output_files, list):
            items = output_files
        else:
            items = []
        
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
        changes = self._get_game_changes(game_id, api_game_data)
        should_update = bool(changes)
        
        if should_update:
            logger.info(f"Game {game_id} status changed: "
                       f"changes={changes}")
        else:
            logger.info(f"Game {game_id} status unchanged - skipping update")
        
        return should_update

    def _get_game_changes(self, game_id: str, api_game_data: Dict[str, Any]) -> List[str]:
        """Explain which tracked provider fields differ from the database."""
        current_status = self.db_session.query(GameStatus).filter(
            GameStatus.game_id == game_id
        ).first()
        if not current_status:
            return ["no_game_status"]

        new_hash = self._calculate_output_files_hash(api_game_data.get("outputFiles", []))
        changes = []
        if current_status.available != api_game_data.get("available", False):
            changes.append("available")
        if current_status.is_ugd_available != api_game_data.get("isUGDAvailable", False):
            changes.append("is_ugd_available")
        if current_status.rgd_status != api_game_data.get("rgdStatus"):
            changes.append("rgd_status")
        if current_status.ugd_status != api_game_data.get("ugdStatus"):
            changes.append("ugd_status")
        if current_status.output_files_hash != new_hash:
            changes.append("output_files")
        return changes
    
    def _delete_game_data(self, game_id: str, task_id: Optional[str] = None, game_name: Optional[str] = None, round_name: Optional[str] = None) -> tuple[bool, Dict[str, Dict[str, int]]]:
        """
        Delete all data associated with a game (for clean re-download)
        
        Deletes all match-specific data in reverse dependency order while
        keeping the Game row itself.
        
        Game record is kept (FK relationships ensure data integrity)
        
        Args:
            game_id: Game ID to delete data for
            task_id: Optional scraping task ID (for logging to DB)
            game_name: Optional game name (for logging)
            round_name: Optional round name (for logging)
            
        Returns:
            Tuple of (success: bool, stats: Dict[table_name -> {deleted: int}])
        """
        try:
            # Count before deletion for logging
            before_counts = {
                'game_status': self.db_session.query(GameStatus).filter(GameStatus.game_id == game_id).count(),
                'output_files': self.db_session.query(OutputFile).filter(OutputFile.game_id == game_id).count(),
                'player_fitness_runs': self.db_session.query(PlayerFitnessRun).filter(PlayerFitnessRun.game_id == game_id).count(),
                'player_fitness_summary': self.db_session.query(PlayerFitnessSummary).filter(PlayerFitnessSummary.game_id == game_id).count(),
                'team_fitness_summary': self.db_session.query(TeamFitnessSummary).filter(TeamFitnessSummary.game_id == game_id).count(),
                'player_distance_covered': self.db_session.query(PlayerDistanceCovered).filter(PlayerDistanceCovered.game_id == game_id).count(),
                'team_distance_covered': self.db_session.query(TeamDistanceCovered).filter(TeamDistanceCovered.game_id == game_id).count(),
                'lineup_player': self.db_session.query(LineupPlayer).join(LineupTeam).filter(LineupTeam.game_id == game_id).count(),
                'lineup_team': self.db_session.query(LineupTeam).filter(LineupTeam.game_id == game_id).count(),
                'game_substitution': self.db_session.query(GameSubstitution).filter(GameSubstitution.game_id == game_id).count(),
                'game_score_evolution': self.db_session.query(GameScoreEvolution).filter(GameScoreEvolution.game_id == game_id).count(),
                'periods': self.db_session.query(Period).filter(Period.game_id == game_id).count(),
                'ball_in_play': self.db_session.query(BallInPlay).filter(BallInPlay.game_id == game_id).count(),
                'card': self.db_session.query(Card).filter(Card.game_id == game_id).count(),
                'foul': self.db_session.query(Foul).filter(Foul.game_id == game_id).count(),
                'goalkick': self.db_session.query(GoalKick).filter(GoalKick.game_id == game_id).count(),
                'goals': self.db_session.query(Goals).filter(Goals.game_id == game_id).count(),
                'kickoff': self.db_session.query(Kickoff).filter(Kickoff.game_id == game_id).count(),
                'offside': self.db_session.query(Offside).filter(Offside.game_id == game_id).count(),
                'phase_of_play': self.db_session.query(PhaseOfPlay).filter(PhaseOfPlay.game_id == game_id).count(),
                'type_of_play': self.db_session.query(TypeOfPlay).filter(TypeOfPlay.game_id == game_id).count(),
                'individual_possession': self.db_session.query(IndividualPossession).filter(IndividualPossession.game_id == game_id).count(),
                'possession_collective': self.db_session.query(PossessionCollective).filter(PossessionCollective.game_id == game_id).count(),
                'setpieces': self.db_session.query(Setpieces).filter(Setpieces.game_id == game_id).count(),
                'events': self.db_session.query(Events).filter(Events.game_id == game_id).count(),
            }
            
            logger.info(f"🗑️  Cleaning game {game_id}:")
            for table, count in before_counts.items():
                if count > 0:
                    logger.info(f"     - {table}: {count} records")
            
            # Log to DB with deletion stats
            delete_stats = {table: {"deleted": count, "inserted": 0} for table, count in before_counts.items() if count > 0}
            _log_to_db(self.db_session, task_id, f"🗑️  Deleting {sum(before_counts.values())} records from {len([c for c in before_counts.values() if c > 0])} tables", 
                       level="INFO", context="game_cleaning", item_id=game_id, item_name=game_name, round_name=round_name, stats=delete_stats)
            
            # Delete dependent records before their referenced event and period rows.
            self.db_session.query(PlayerFitnessRun).filter(PlayerFitnessRun.game_id == game_id).delete(synchronize_session=False)
            self.db_session.query(PlayerFitnessSummary).filter(PlayerFitnessSummary.game_id == game_id).delete(synchronize_session=False)
            self.db_session.query(TeamFitnessSummary).filter(TeamFitnessSummary.game_id == game_id).delete(synchronize_session=False)
            self.db_session.query(PlayerDistanceCovered).filter(PlayerDistanceCovered.game_id == game_id).delete(synchronize_session=False)
            self.db_session.query(TeamDistanceCovered).filter(TeamDistanceCovered.game_id == game_id).delete(synchronize_session=False)

            # Delete match-specific events and RGD analytics.
            for model in (
                Setpieces, IndividualPossession, PossessionCollective,
                BallInPlay, Card, Foul, GoalKick, Goals, Kickoff, Offside,
                PhaseOfPlay, TypeOfPlay,
            ):
                self.db_session.query(model).filter(model.game_id == game_id).delete(synchronize_session=False)

            self.db_session.query(Events).filter(Events.game_id == game_id).delete(synchronize_session=False)

            # Delete periods and score evolution.
            self.db_session.query(GameScoreEvolution).filter(GameScoreEvolution.game_id == game_id).delete(synchronize_session=False)
            self.db_session.query(Period).filter(Period.game_id == game_id).delete(synchronize_session=False)

            # Delete remaining match-specific events.
            self.db_session.query(GameSubstitution).filter(GameSubstitution.game_id == game_id).delete()
            
            # 5. Delete lineup data (LineupPlayer → LineupTeam)
            # First delete LineupPlayers that reference LineupTeams for this game
            lineup_teams = self.db_session.query(LineupTeam).filter(LineupTeam.game_id == game_id).all()
            for lineup_team in lineup_teams:
                self.db_session.query(LineupPlayer).filter(LineupPlayer.lineup_team_id == lineup_team.id).delete()
            self.db_session.query(LineupTeam).filter(LineupTeam.game_id == game_id).delete()
            
            # 6. Delete output files metadata
            self.db_session.query(OutputFile).filter(OutputFile.game_id == game_id).delete()
            
            # Delete tracking records last.
            self.db_session.query(GameStatus).filter(GameStatus.game_id == game_id).delete()
            
            self.db_session.commit()
            logger.info(f"✅ Successfully cleaned all data for game {game_id}")
            
            return True, delete_stats
            
        except Exception as e:
            logger.error(f"❌ Failed to delete game data for {game_id}: {e}", exc_info=True)
            self.db_session.rollback()
            return False, {}

    def _log_game_insert_stats(self, game: Game) -> None:
        """Log rows present after a successful game parse for task monitoring."""
        if not self.task_id:
            return

        stats = {
            "game_status": {"deleted": 0, "inserted": self.db_session.query(GameStatus).filter(GameStatus.game_id == game.id).count()},
            "output_files": {"deleted": 0, "inserted": self.db_session.query(OutputFile).filter(OutputFile.game_id == game.id).count()},
            "events": {"deleted": 0, "inserted": self.db_session.query(Events).filter(Events.game_id == game.id).count()},
            "periods": {"deleted": 0, "inserted": self.db_session.query(Period).filter(Period.game_id == game.id).count()},
            "game_score_evolution": {"deleted": 0, "inserted": self.db_session.query(GameScoreEvolution).filter(GameScoreEvolution.game_id == game.id).count()},
            "lineup_player": {"deleted": 0, "inserted": self.db_session.query(LineupPlayer).join(LineupTeam).filter(LineupTeam.game_id == game.id).count()},
            "lineup_team": {"deleted": 0, "inserted": self.db_session.query(LineupTeam).filter(LineupTeam.game_id == game.id).count()},
            "game_substitution": {"deleted": 0, "inserted": self.db_session.query(GameSubstitution).filter(GameSubstitution.game_id == game.id).count()},
            "setpieces": {"deleted": 0, "inserted": self.db_session.query(Setpieces).filter(Setpieces.game_id == game.id).count()},
            "individual_possession": {"deleted": 0, "inserted": self.db_session.query(IndividualPossession).filter(IndividualPossession.game_id == game.id).count()},
            "possession_collective": {"deleted": 0, "inserted": self.db_session.query(PossessionCollective).filter(PossessionCollective.game_id == game.id).count()},
            "team_distance_covered": {"deleted": 0, "inserted": self.db_session.query(TeamDistanceCovered).filter(TeamDistanceCovered.game_id == game.id).count()},
            "player_distance_covered": {"deleted": 0, "inserted": self.db_session.query(PlayerDistanceCovered).filter(PlayerDistanceCovered.game_id == game.id).count()},
            "player_fitness_runs": {"deleted": 0, "inserted": self.db_session.query(PlayerFitnessRun).filter(PlayerFitnessRun.game_id == game.id).count()},
            "player_fitness_summary": {"deleted": 0, "inserted": self.db_session.query(PlayerFitnessSummary).filter(PlayerFitnessSummary.game_id == game.id).count()},
            "team_fitness_summary": {"deleted": 0, "inserted": self.db_session.query(TeamFitnessSummary).filter(TeamFitnessSummary.game_id == game.id).count()},
        }
        _log_to_db(
            self.db_session,
            self.task_id,
            f"✅ Inserted rows for {game.name}",
            level="INFO",
            context="game_persistence",
            item_id=game.id,
            item_name=game.name,
            round_name=game.round_name,
            stats=stats,
        )
        self.db_session.commit()
    
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
                
                # CREATE TEAMS IF THEY DON'T EXIST
                # This ensures FK constraints are satisfied before game INSERT
                for team_id, team_name in [(home_team_id, home_team_name), (away_team_id, away_team_name)]:
                    if team_id:
                        existing_team = self.db_session.query(Team).filter(Team.id == team_id).first()
                        if not existing_team:
                            logger.info(f"   Creating missing team: {team_name} (id={team_id})")
                            new_team = Team(
                                id=team_id,
                                name=team_name or f"Team {team_id[:8]}",
                                brand=team_name or f"Team {team_id[:8]}"
                            )
                            self.db_session.add(new_team)
                            self.db_session.flush()  # Flush to make team available for FK references
                
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
                    round=raw.get("round", {}).get("name"),  # Fill both round and round_name
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
        
        # Create a map of game_id -> raw_game_data for lookup
        raw_games_map = {game.get("id"): game for game in raw_games}
        
        # Force all games with outputFiles to persist (ignore status unchanged for outputFiles)
        # This is needed because API might not return outputFiles when status unchanged
        for game in orm_games:
            raw_data = raw_games_map.get(game.id)
            if raw_data:
                output_files_data = raw_data.get("outputFiles", {})
                if output_files_data and output_files_data.get("items"):
                    logger.info(f"📥 Pre-loading outputFiles for {game.id}: {len(output_files_data.get('items', []))} items from API response")
                    output_files_to_persist[game.id] = output_files_data
        
        for game in orm_games:
            try:
                raw_data = raw_games_map.get(game.id)
                if not raw_data:
                    logger.warning(f"No raw data found for game {game.id} - skipping")
                    continue
                
                # 🔍 FK Diagnostic: Check if teams and season exist before insert
                team_1_exists = self.db_session.query(Team).filter(Team.id == game.home_team_id).first() is not None
                team_2_exists = self.db_session.query(Team).filter(Team.id == game.away_team_id).first() is not None
                season_exists = self.db_session.query(Season).filter(Season.id == game.season_id).first() is not None
                if not (team_1_exists and team_2_exists and season_exists):
                    logger.warning(f"🔍 FK Check for game {game.id}: team_1_exists={team_1_exists}, team_2_exists={team_2_exists}, season_exists={season_exists}")
                
                # 📁 Check output files before processing
                raw_output_files = raw_data.get("outputFiles", {})
                logger.info(f"🔍 Game {game.name}: outputFiles type={type(raw_output_files).__name__}, has_data={bool(raw_output_files)}")
                if isinstance(raw_output_files, dict):
                    items = raw_output_files.get("items", [])
                    logger.info(f"   → {len(items)} items in outputFiles")
                
                # 📊 Check if game needs update
                if not self._should_update_game(game.id, raw_data):
                    logger.info(f"⏭️  Skipping game {game.id} - status unchanged")
                    # Still need to return it for API response
                    existing = self.db_session.query(Game).filter(Game.id == game.id).first()
                    if existing:
                        saved_games.append(existing)
                    # ✅ IMPORTANT: Still need to process output files even if status unchanged
                    # because metadata may have become newly available
                    # If API doesn't return outputFiles for unchanged status, use stored raw_data OR make separate API call
                    output_files_data = raw_data.get("outputFiles", {})
                    logger.info(f"   📁 API returned outputFiles with {len(output_files_data.get('items', []))} items")
                    
                    # If API returns empty, try separate query for this specific game
                    if not output_files_data.get("items"):
                        logger.info(f"   🔄 Making separate API call for outputFiles of {game.id}")
                        try:
                            separate_output_files = self.provider.get_game_output_files(game.id)
                            items_count = len(separate_output_files.get("items", []))
                            logger.info(f"   ✅ Separate API call returned {items_count} outputFiles items")
                            if items_count > 0:
                                output_files_data = separate_output_files
                        except Exception as e:
                            logger.warning(f"   ⚠️  Separate API call failed: {e}")
                    
                    # If still empty, try stored raw_data as fallback
                    if not output_files_data.get("items"):
                        if existing and existing.raw_data:
                            try:
                                # Ensure raw_data is hydrated
                                stored_raw = existing.raw_data
                                if isinstance(stored_raw, str):
                                    import json as json_module
                                    stored_raw = json_module.loads(stored_raw)
                                stored_output_files = stored_raw.get("outputFiles", {}) if isinstance(stored_raw, dict) else {}
                                stored_items = stored_output_files.get("items", [])
                                logger.info(f"   📁 Stored raw_data has {len(stored_items)} outputFiles items")
                                if stored_items:
                                    logger.info(f"   ℹ️  Using stored outputFiles from database for {game.id}")
                                    output_files_data = stored_output_files
                            except Exception as e:
                                logger.warning(f"   ⚠️  Failed to extract stored outputFiles: {e}")
                    
                    if output_files_data and output_files_data.get("items"):  # Only add if has items
                        logger.info(f"   ✅ Adding {len(output_files_data.get('items', []))} output files to persist queue")
                        output_files_to_persist[game.id] = output_files_data
                    continue
                
                # 🗑️ Delete old data if game exists
                existing = self.db_session.query(Game).filter(Game.id == game.id).first()
                if existing:
                    logger.info(f"🗑️  Deleting old data for game {game.id} (status changed)")
                    game_name = f"{game.name}" if game.name else f"Game {game.id[:8]}"
                    round_name = raw_data.get("round") if raw_data else None
                    self._delete_game_data(game.id, task_id=self.task_id, game_name=game_name, round_name=round_name)
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
                logger.info(f"     📁 OutputFiles for {game.id[:8]}: has_data={bool(output_files_data)}, items={len(output_files_list)}")
                output_files_to_persist[game.id] = output_files_data
                
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
        
        if len(output_files_to_persist) == 0:
            logger.warning(f"⚠️  output_files_to_persist is empty! This means:")
            logger.warning(f"     - Either API returned no outputFiles in raw_games")
            logger.warning(f"     - Or the check 'if output_files_data' filtered them out")
            logger.warning(f"     - Checking raw_games sample...")
            if raw_games and len(raw_games) > 0:
                sample = raw_games[0]
                logger.warning(f"     - First game name: {sample.get('name')}")
                logger.warning(f"     - Has outputFiles? {bool(sample.get('outputFiles'))}")
                if sample.get('outputFiles'):
                    logger.warning(f"       outputFiles items count: {len(sample.get('outputFiles', {}).get('items', []))}")
        
        for game_id, output_files_data in output_files_to_persist.items():
            try:
                # Load game to get its name
                game = self.db_session.query(Game).filter(Game.id == game_id).first()
                if not game:
                    logger.warning(f"⚠️  Game {game_id} not found when persisting output files")
                    continue
                
                self._persist_output_files(game_id, output_files_data)
                # 📥 Download JSON files from S3 URLs (in-memory)
                downloaded_data = self._download_json_output_files(game_id, game.name, output_files_data)
                
                # 📊 Process metadata.json (lineups, periods, events)
                if "metadata" in downloaded_data:
                    self._process_metadata_json(game, downloaded_data["metadata"])
                # 📊 Process rgd.json before fitness entities because fitness rows
                # reference RGD event records.
                if "rgd" in downloaded_data:
                    self._process_rgd_json(game, game.name, downloaded_data["rgd"])
                # 📏 Process distance_covered.json (team distances)
                if "distance_covered" in downloaded_data:
                    self._process_distance_covered_json(game, downloaded_data["distance_covered"], downloaded_data.get("metadata"))
                # 💪 Process fitness_entities.json (player fitness runs)
                if "fitness_entities" in downloaded_data:
                    self._process_fitness_entities_json(game, downloaded_data["fitness_entities"])
                    
            except Exception as e:
                logger.warning(f"❌ Failed to persist/download/process files for {game_id}: {e}", exc_info=True)
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
        
        # � Log final status
        logger.info(f"✅ Persisting complete: {len(saved_games)} games processed")
        
        # 📊 Upsert GameSummary records for each game
        # NOTE: game_summary table doesn't exist yet (no migration created), so skip for now
        # Extracted game IDs and data BEFORE the commit expires the objects
        # games_to_summarize = []
        # for game in saved_games:
        #     games_to_summarize.append({
        #         'id': game.id,
        #         'name': game.name,
        #         'object': game
        #     })
        # 
        # for game_info in games_to_summarize:
        #     try:
        #         raw_data = raw_games_map.get(game_info['id'])
        #         if raw_data:
        #             # available = True if game was successfully processed
        #             self._upsert_game_summary(game_info['object'], raw_data, available=True)
        #     except Exception as e:
        #         logger.warning(f"⚠️  Failed to upsert summary for {game_info['id']}: {e}")
        #         continue
        
        # Final commit for GameSummary
        # NOTE: Skipped since game_summary table doesn't exist yet
        # try:
        #     self.db_session.commit()
        #     logger.info(f"✅ Committed GameSummary records")
        # except Exception as e:
        #     logger.error(f"❌ GameSummary commit failed: {e}", exc_info=True)
        #     self.db_session.rollback()
        
        return saved_games
    
    def _persist_games_basic(self, orm_games: List[Game], raw_games: List[Dict[str, Any]]) -> List[Game]:
        """
        Persist ONLY basic game information without downloading JSON files
        
        Perfect for season initialization. Does NOT:
        - Download 4 JSON files
        - Parse lineups/events/fitness
        - Export files to disk
        
        DOES:
        - Create/update Game records
        - Create/update Team records
        
        Args:
            orm_games: List of Game ORM instances
            raw_games: List of raw API response dicts
            
        Returns:
            List of persisted Game instances
        """
        logger.info(f"💾 Persisting {len(orm_games)} games (SCHEDULE ONLY - no JSON files)...")
        saved_games = []
        
        # Create a map of game_id -> raw_game_data for lookup
        raw_games_map = {game.get("id"): game for game in raw_games}
        
        for game in orm_games:
            try:
                raw_data = raw_games_map.get(game.id)
                if not raw_data:
                    logger.warning(f"No raw data found for game {game.id} - skipping")
                    continue
                
                # Schedule initialization updates only the general Game fields.
                # It must not inspect status or delete match-specific data.
                existing = self.db_session.query(Game).filter(Game.id == game.id).first()
                if existing:
                    logger.info(f"↻ Updating schedule data for game {game.id}")
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
                
            except Exception as e:
                logger.warning(f"❌ Failed to persist game {game.id}: {e}", exc_info=True)
                continue
        
        # Commit all changes
        try:
            logger.info(f"💾 Committing {len(saved_games)} games to database...")
            self.db_session.commit()
            logger.info(f"✅ Committed {len(saved_games)} games to database (schedule only)")
        except Exception as e:
            logger.error(f"❌ Database commit failed: {e}", exc_info=True)
            self.db_session.rollback()
            raise
        
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
            logger.info(f"🔍 _persist_output_files for game {game_id}: output_files_data type={type(output_files_data).__name__}, keys={list(output_files_data.keys()) if isinstance(output_files_data, dict) else 'N/A'}")
            output_files = output_files_data.get("items", [])
            logger.info(f"   → Found {len(output_files)} items")
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
    
    def _download_json_output_files(
        self,
        game_id: str,
        game_name: str,
        output_files_data: Dict[str, Any],
        refresh_expired_urls: bool = True,
    ) -> Dict[str, Any]:
        """
        Download JSON output files from S3 URLs into RAM, parse them, and export to disk.
        
        Flow:
        1. Download JSON to RAM (BytesIO)
        2. Parse JSON in memory (no disk I/O)
        3. Export parsed JSON to disk for access by parsers
        4. RAM is freed after each file (data goes out of scope)
        
        This hybrid approach optimizes RAM usage for 9-game batches:
        - Only ~30 MB RAM used at peak (1 game's JSONs)
        - Files available on disk for parser functions
        
        Args:
            game_id: Game ID
            game_name: Game name for directory organization
            output_files_data: outputFiles dict from API (structure: {"items": [...]})
            
        Returns:
            Dict mapping json_type -> parsed json data (or empty dict if errors)
        """
        try:
            # Extract items array from outputFiles structure
            output_files = output_files_data.get("items", [])
            
            # ⚠️ CHECK FOR EMPTY outputFiles - CRITICAL FOR DIAGNOSIS
            if not output_files:
                logger.warning(f"⚠️  CRITICAL: No JSON files available for game {game_name} (game_id: {game_id})")
                logger.warning(f"    outputFiles is empty - this means the API did not return file URLs")
                logger.warning(f"    Likely causes:")
                logger.warning(f"      1. Files are not yet processed by SportsDynamics backend")
                logger.warning(f"      2. Permissions issue - your API key may not have access")
                logger.warning(f"      3. Game status incomplete - check rgdStatus and available fields")
                logger.warning(f"    Action: Check game status in database and wait for files to be available")
                logger.warning(f"    Tables periods and setpieces will remain empty until outputFiles become available")
                return {}
            
            logger.info(f"📥 Downloading JSON files into RAM for game {game_name}...")
            
            # JSON type mapping
            json_type_map = {
                "metadata": "metadata",
                "fitness_entities": "fitness_entities",
                "distance_covered": "distance_covered",
                "rgd": "rgd",
            }
            
            downloaded_data = {}  # Store parsed JSON data temporarily
            json_file_names = {}
            
            for file_item in output_files:
                # Only download JSON files
                if file_item.get("fileType") != "JSON":
                    continue
                
                file_name = file_item.get("fileName", "")
                file_info = file_item.get("file", {})
                url = file_info.get("url")
                
                if not url:
                    logger.warning(f"  ⚠️  No URL for {file_name}")
                    continue
                
                # Detect JSON type from filename
                json_type = None
                normalized_file_name = file_name.lower()
                for pattern, json_type_name in json_type_map.items():
                    if normalized_file_name.startswith(pattern + "_"):
                        json_type = json_type_name
                        break
                
                if not json_type:
                    logger.warning(f"  ⚠️  Unknown JSON type: {file_name}")
                    continue
                
                try:
                    logger.info(f"  📥 Downloading {json_type} to RAM...")
                    
                    # 1️⃣ Download to RAM using urlopen + BytesIO
                    response = urllib.request.urlopen(url)
                    json_bytes = response.read()  # Read into RAM
                    file_size = len(json_bytes)
                    
                    # 2️⃣ Parse JSON in memory (no disk I/O yet)
                    json_data = json.loads(json_bytes)
                    logger.info(f"    ✅ Downloaded & parsed {json_type} ({file_size:,} bytes)")
                    
                    # Store parsed data
                    downloaded_data[json_type] = json_data
                    json_file_names[json_type] = file_name
                    logger.info(f"    ✅ Downloaded & parsed {json_type} ({file_size:,} bytes)")
                    
                    # No disk export needed - parsers receive data in-memory!
                    
                    # 4️⃣ RAM is freed after json_bytes and json_data go out of scope
                    # (Python GC collects them when reference count drops)
                    
                except HTTPError as e:
                    logger.warning(f"    ⚠️  HTTP {e.code} for {json_type} - URL may have expired")
                except URLError as e:
                    logger.warning(f"    ⚠️  URL error for {json_type}: {str(e)}")
                except json.JSONDecodeError as e:
                    logger.warning(f"    ⚠️  Failed to parse {json_type}: {e}")
                except Exception as e:
                    logger.warning(f"    ⚠️  Error downloading {json_type}: {str(e)}")
            
            logger.info(
                f"✅ JSON download complete for game {game_name}: "
                f"types={sorted(downloaded_data)}, files={json_file_names}"
            )
            expected_types = {"metadata", "rgd", "distance_covered", "fitness_entities"}
            missing_types = sorted(expected_types - downloaded_data.keys())
            if missing_types:
                logger.warning(
                    f"⚠️  Missing JSON types for game {game_name}: {missing_types}"
                )
                if refresh_expired_urls:
                    logger.info(
                        f"🔄 Refreshing output-file URLs for game {game_name}"
                    )
                    refreshed_files = self.provider.get_game_output_files(game_id)
                    if refreshed_files.get("items"):
                        return self._download_json_output_files(
                            game_id,
                            game_name,
                            refreshed_files,
                            refresh_expired_urls=False,
                        )
            
            return downloaded_data
            
        except Exception as e:
            logger.error(f"❌ Failed to download JSON files for {game_name}: {e}", exc_info=True)
            # Don't raise - allow scraping to continue even if JSON download fails
            return {}
    
    def _process_metadata_json(self, game: Game, metadata_json: Dict[str, Any]) -> None:
        """
        Process downloaded metadata.json and persist lineups, periods, and events.
        
        This function is called after JSON files are downloaded and processes the metadata
        to extract and persist:
        - Lineups (from metadata['lineups'])
        - Periods with score evolution (from metadata['periods'])
        - Match events (from metadata['events'])
        
        Args:
            game: Game ORM object
            metadata_json: Metadata dict from downloaded JSON
        """
        try:
            if not metadata_json:
                logger.info(f"ℹ️  No metadata JSON provided for game {game.id}")
                return
            
            # Process lineups
            try:
                logger.info(f"👥 Processing lineups for game {game.id}...")
                parse_and_persist_lineups(game, metadata_json, self.db_session)
                logger.info(f"✅ Lineups processed for game {game.id}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to process lineups for {game.id}: {e}", exc_info=True)
                self.db_session.rollback()  # Clean session after error
            
            # Process periods and score evolution
            try:
                logger.info(f"📊 Processing periods for game {game.id}...")
                parse_and_persist_periods(game, metadata_json, self.db_session)
                logger.info(f"✅ Periods processed for game {game.id}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to process periods for {game.id}: {e}", exc_info=True)
                self.db_session.rollback()  # Clean session after error
            
            # Process substitution events
            try:
                logger.info(f"⚽ Processing substitutions for game {game.id}...")
                parse_and_persist_substitutions(game, metadata_json, self.db_session)
                logger.info(f"✅ Substitutions processed for game {game.id}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to process substitutions for {game.id}: {e}", exc_info=True)
                self.db_session.rollback()  # Clean session after error
            
        except Exception as e:
            logger.error(f"❌ Failed to process metadata for {game.id}: {e}", exc_info=True)
            # Don't raise - allow scraping to continue even if metadata processing fails
    
    def _build_player_to_team_mapping_from_metadata(self, metadata_json: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract player_id → team_id mapping from metadata JSON data (in-memory).
        
        This allows us to associate players with their teams in distance_covered data.
        The metadata JSON contains lineups with team_id and player list.
        
        Args:
            metadata_json: Parsed metadata JSON data (dict)
            
        Returns:
            Dict mapping player_id → team_id
        """
        try:
            if not metadata_json:
                return {}
            
            # Extract lineups from metadata
            lineups = metadata_json.get('metadata', {}).get('lineups', [])
            if not lineups:
                logger.debug(f"⚠️  No lineups found in metadata JSON")
                return {}
            
            # Build player_id → team_id mapping
            mapping = {}
            for lineup in lineups:
                team_id = lineup.get('id')  # team_id is stored as 'id' in lineups array
                players = lineup.get('players', [])
                for player_data in players:
                    player_id = player_data.get('id')
                    if player_id and team_id:
                        mapping[player_id] = team_id
            
            logger.debug(f"✅ Built player→team mapping from metadata JSON: {len(mapping)} players from {len(lineups)} teams")
            return mapping
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to build player→team mapping from metadata JSON: {e}")
            return {}
    
    def _process_distance_covered_json(self, game: Game, distance_json: Dict[str, Any], metadata_json: Dict[str, Any] = None) -> None:
        """
        Process distance_covered JSON data and persist team distance records.
        
        Args:
            game: Game ORM object
            distance_json: Parsed distance_covered JSON data (dict)
            metadata_json: Parsed metadata JSON data for player→team mapping (optional)
        """
        try:
            if not distance_json:
                logger.info(f"ℹ️  No distance_covered JSON data for game {game.id}")
                return
            
            # Process distance covered
            try:
                logger.info(f"📏 Processing distance covered for game {game.id}...")
                parse_and_persist_distance_covered(game, distance_json, self.db_session)
                logger.info(f"✅ Distance covered processed for game {game.id}")
                
                # Build player→team mapping from metadata JSON (in-memory, no disk reads)
                team_mapping = self._build_player_to_team_mapping_from_metadata(metadata_json) if metadata_json else {}
                
                # Process player distance covered with team mapping
                logger.info(f"👥 Processing player distance covered for game {game.id}...")
                parse_and_persist_player_distance_covered(game, distance_json, self.db_session, team_mapping=team_mapping)
                logger.info(f"✅ Player distance covered processed for game {game.id}")
                
                # Commit changes to database
                self.db_session.commit()
                logger.info(f"💾 Committed distance_covered data for game {game.id}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to process distance_covered for {game.id}: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"❌ Failed to process distance_covered for {game.id}: {e}", exc_info=True)
            # Don't raise - allow scraping to continue even if distance processing fails
    
    def _process_fitness_entities_json(self, game: Game, fitness_json: Dict[str, Any]) -> None:
        """
        Process fitness_entities JSON data and persist player fitness records.
        
        Args:
            game: Game ORM object
            fitness_json: Parsed fitness_entities JSON data (dict)
        """
        try:
            if not fitness_json:
                logger.info(f"ℹ️  No fitness_entities JSON data for game {game.id}")
                return
            
            # Process fitness entities
            try:
                logger.info(f"💪 Processing fitness entities for game {game.id}...")
                parse_and_persist_fitness_entities(
                    game=game,
                    fitness_data=fitness_json,
                    db_session=self.db_session,
                    calculate_summaries=True
                )
                logger.info(f"✅ Fitness entities processed for game {game.id}")
                
                # Commit changes to database
                self.db_session.commit()
                logger.info(f"💾 Committed fitness_entities data for game {game.id}")
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to process fitness_entities for {game.id}: {e}", exc_info=True)
                # Rollback on error to avoid partial data
                self.db_session.rollback()
            
        except Exception as e:
            logger.error(f"❌ Failed to process fitness_entities for {game.id}: {e}", exc_info=True)
            # Don't raise - allow scraping to continue even if fitness processing fails
    
    def _process_rgd_json(
        self,
        game: Game,
        game_name: str,
        rgd_json_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Process downloaded rgd.json file and persist event data.
        
        This function is called after JSON files are downloaded and processes the rgd.json
        to extract and persist:
        - Events table (~3,000+ entities per match)
        - Possession collective records (~200 per match)
        - Individual possession records (~1,200 per match)
        - Set pieces records (~110 per match)
        
        RGD (Relative Game Data) is the complete match dump with all spatial/temporal data.
        
        Args:
            game_name: Game name for directory organization
            game: Game ORM object
        """
        try:
            logger.info(f"📊 Processing RGD events for game {game.id}...")
            
            # Parse and persist RGD data
            result = parse_and_persist_rgd(
                game=game,
                game_name=game_name,
                db_session=self.db_session,
                rgd_json_data=rgd_json_data,
                clean_existing=True,
                task_id=self.task_id,
                round_name=game.round
            )
            events, collective, individual, setpieces, errors = result
            entity_count = len((rgd_json_data or {}).get("entities", []))
            logger.info(
                f"✅ RGD events processed for game {game.id}: "
                f"entities={entity_count}, events={events}, "
                f"collective={collective}, individual={individual}, "
                f"setpieces={setpieces}, errors={errors}"
            )
            if entity_count and not events:
                raise RuntimeError(
                    f"RGD contained {entity_count} entities but inserted no events"
                )
            
            # Commit changes to database
            self.db_session.commit()
            logger.info(f"💾 Committed RGD data for game {game.id}")
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to process RGD for {game.id}: {e}", exc_info=True)
            # Rollback on error to avoid partial data
            self.db_session.rollback()
    
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
    
    def _create_default_periods_for_games(self, games: List[Game]) -> None:
        """
        Create default periods (1st half, 2nd half) for games that don't have them yet.
        
        This is a temporary solution until metadata.json files become available from SportsDynamics.
        Each game gets 2 default periods with minimal metadata.
        
        Args:
            games: List of Game ORM objects to process
        """
        try:
            from uuid import uuid4
            
            # Find games without periods - refresh from DB to avoid cached relationships
            games_needing_periods = []
            for g in games:
                # Explicitly query DB to check if this game has periods (don't use cached relationship)
                existing_periods = self.db_session.query(Period).filter(Period.game_id == g.id).count()
                if existing_periods == 0:
                    games_needing_periods.append(g)
            
            if not games_needing_periods:
                logger.info(f"✅ All {len(games)} games already have periods")
                return
            
            periods_created = 0
            
            # Create 2 default periods for each game
            for game in games_needing_periods:
                for period_num in [1, 2]:
                    period = Period(
                        id=str(uuid4()),
                        game_id=game.id,
                        period_id=period_num,
                        time=None,  # Will be filled when metadata.json becomes available
                        direction=None  # Will be filled when metadata.json becomes available
                    )
                    self.db_session.add(period)
                    periods_created += 1
            
            # Commit all periods
            self.db_session.commit()
            logger.info(f"📊 PERIODS TABLE: {periods_created} rows created for {len(games_needing_periods)} games")
            logger.info(f"   {len(games)} total games in batch - {len(games_needing_periods)} needed periods")
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to create default periods: {e}", exc_info=True)
            raise

