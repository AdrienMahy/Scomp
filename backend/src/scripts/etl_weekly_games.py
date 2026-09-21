#!/usr/bin/env python3
"""
Weekly ETL Script - Injection 2
Processes unprocessed games and detects updates via hash comparison

Mode: Weekly
Flow:
1. Query BD for games with data_processed=False
2. For each game (sequential, no multi-threading):
   - Get current outputFiles from API
   - If GameStatus exists: compare hash
     - If hash differs: delete orphan data + re-ETL
     - If same: skip
   - If no GameStatus: ETL new data
3. Mark data_processed=True when complete
4. Log results (goals, cards, lineups counts)
"""

import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from ..models.game import Game
from ..models.game_status import GameStatus
from ..orchestration.scraper_coordinator import ScraperCoordinator
from ..config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/etl_weekly.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WeeklyETLProcessor:
    """Process unprocessed games with update detection"""
    
    def __init__(self):
        """Initialize processor with internal database session"""
        from ..config.database import SessionLocal
        self.db_session = SessionLocal()
        self.coordinator = ScraperCoordinator()
        self.stats = {
            'total_games': 0,
            'skipped': 0,
            'etl_new': 0,
            'etl_updated': 0,
            'errors': 0,
            'total_goals': 0,
            'total_cards': 0,
            'total_lineups': 0
        }
    
    def run(self, league_name: str = "Ligue 2", season_name: str = "2026 - 2027", 
            limit_games: Optional[int] = None, round_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Main ETL execution
        
        Args:
            league_name: League to process
            season_name: Season to process
            limit_games: Max games to process (for testing)
            round_name: Optional round to filter (e.g., "1" for Round 1)
        
        Returns:
            Dictionary with stats
        """
        logger.info("=" * 80)
        logger.info(f"🚀 Starting Weekly ETL - {league_name} {season_name}")
        if round_name:
            logger.info(f"📌 Filtering for Round: {round_name}")
        logger.info("=" * 80)
        
        try:
            # Get all unprocessed games
            query = self.db_session.query(Game).filter(
                Game.data_processed == False
            )
            
            # Filter by round if specified
            if round_name:
                query = query.filter(Game.round_name == round_name)
            
            unprocessed_games = query.all()
            
            if not unprocessed_games:
                logger.info("✅ No unprocessed games found")
                return self.stats
            
            logger.info(f"📋 Found {len(unprocessed_games)} unprocessed games")
            
            # Process each game sequentially
            for idx, game in enumerate(unprocessed_games[:limit_games], 1):
                logger.info(f"\n[{idx}/{len(unprocessed_games)}] Processing: {game.name}")
                self._process_game(game)
            
            logger.info("\n" + "=" * 80)
            logger.info("📊 SUMMARY:")
            logger.info(f"  Total games processed: {self.stats['total_games']}")
            logger.info(f"  New ETL: {self.stats['etl_new']}")
            logger.info(f"  Updated (hash changed): {self.stats['etl_updated']}")
            logger.info(f"  Skipped (no change): {self.stats['skipped']}")
            logger.info(f"  Errors: {self.stats['errors']}")
            logger.info(f"  Total events:")
            logger.info(f"    - Goals: {self.stats['total_goals']}")
            logger.info(f"    - Cards: {self.stats['total_cards']}")
            logger.info(f"    - Lineups: {self.stats['total_lineups']}")
            logger.info("=" * 80)
            
            return self.stats
            
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            raise
    
    def _process_game(self, game: Game) -> None:
        """
        Process single game with update detection
        
        1. Get outputFiles from game.raw_data (set during Injection 1)
        2. Check GameStatus for hash
        3. If exists: compare with current outputFiles hash
           - If changed: delete GameStatus + ETL
           - If same: skip
        4. If not exists: ETL new
        """
        try:
            # Extract outputFiles from raw_data (set during Schedule mode)
            output_files = game.raw_data.get("outputFiles", {}) if game.raw_data else {}
            
            if not output_files.get("items"):
                logger.info(f"  ⚠️  No outputFiles in game.raw_data, skipping")
                self.stats['skipped'] += 1
                return
            
            # Get game status if exists
            status = self.db_session.query(GameStatus).filter(
                GameStatus.game_id == game.id
            ).first()
            
            # Calculate current hash
            current_hash = self.coordinator._calculate_output_files_hash(output_files)
            
            if status:
                # Game already processed before
                if status.output_files_hash == current_hash:
                    logger.info(f"  ✅ No changes detected (hash match)")
                    self.stats['skipped'] += 1
                    return
                else:
                    # Hash changed - delete GameStatus and re-ETL
                    logger.info(f"  🔄 Hash changed - deleting GameStatus...")
                    self._delete_game_status(game.id)
                    logger.info(f"  📥 Re-ETLing updated data...")
                    self._etl_game_data(game, output_files)
                    self.stats['etl_updated'] += 1
            else:
                # First time processing this game
                logger.info(f"  ✨ New game - ETLing data...")
                self._etl_game_data(game, output_files)
                self.stats['etl_new'] += 1
            
            # Mark as processed
            game.data_processed = True
            self.db_session.commit()
            logger.info(f"  ✅ Marked as processed: data_processed=True")
            self.stats['total_games'] += 1
            
        except Exception as e:
            logger.error(f"  ❌ Error processing {game.id}: {e}", exc_info=True)
            self.db_session.rollback()
            self.stats['errors'] += 1
    
    def _delete_game_status(self, game_id: str) -> None:
        """
        Delete GameStatus record for a game
        
        This allows re-processing with new hash comparison
        """
        try:
            self.db_session.query(GameStatus).filter(
                GameStatus.game_id == game_id
            ).delete()
            self.db_session.commit()
            logger.info(f"    Deleted GameStatus for {game_id}")
        except Exception as e:
            logger.error(f"    Failed to delete GameStatus: {e}")
            self.db_session.rollback()
            raise
    
    def _etl_game_data(self, game: Game, output_files: Dict[str, Any]) -> None:
        """
        ETL game data from outputFiles using coordinator
        
        Uses coordinator methods to:
        - Persist outputFiles references
        - Download JSON files
        - Parse metadata (lineups, events)
        - Parse distance data
        - Parse fitness entities
        """
        try:
            # Refresh game object to get current state
            self.db_session.refresh(game)
            
            # Count events BEFORE ETL
            goals_before = len(game.goals) if game.goals else 0
            cards_before = len(game.cards) if game.cards else 0
            lineups_before = sum(
                len(lineup.players) 
                for lineup in (game.lineups or [])
            ) if game.lineups else 0
            
            # Use coordinator's existing methods
            logger.info(f"    Persisting output files references...")
            self.coordinator._persist_output_files(game.id, output_files)
            
            logger.info(f"    Downloading JSON files...")
            self.coordinator._download_json_output_files(game.id, game.name, output_files)
            
            logger.info(f"    Processing metadata (lineups, events)...")
            self.coordinator._process_metadata_json(game.name, game)
            
            logger.info(f"    Processing distance data...")
            self.coordinator._process_distance_covered_json(game.name, game)
            
            logger.info(f"    Processing fitness entities...")
            self.coordinator._process_fitness_entities_json(game.name, game)
            
            logger.info(f"    Processing RGD events...")
            self.coordinator._process_rgd_json(game, game.name)
            
            # Refresh to get new counts
            self.db_session.refresh(game)
            
            # Count events AFTER ETL
            goals_after = len(game.goals) if game.goals else 0
            cards_after = len(game.cards) if game.cards else 0
            lineups_after = sum(
                len(lineup.players) 
                for lineup in (game.lineups or [])
            ) if game.lineups else 0
            
            # Calculate new events
            goals_new = max(0, goals_after - goals_before)
            cards_new = max(0, cards_after - cards_before)
            lineups_new = max(0, lineups_after - lineups_before)
            
            # Update stats
            self.stats['total_goals'] += goals_new
            self.stats['total_cards'] += cards_new
            self.stats['total_lineups'] += lineups_new
            
            logger.info(f"    ✅ ETL complete: {goals_new} new goals | {cards_new} new cards | {lineups_new} new lineups")
            
        except Exception as e:
            logger.error(f"    ETL failed: {e}", exc_info=True)
            self.db_session.rollback()
            raise


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Weekly ETL Processor")
    parser.add_argument('--league', default="Ligue 2", help="League name")
    parser.add_argument('--season', default="2026 - 2027", help="Season name")
    parser.add_argument('--limit', type=int, default=None, help="Limit number of games to process")
    
    args = parser.parse_args()
    
    # Process
    db_session = next(get_session())
    processor = WeeklyETLProcessor(db_session)
    stats = processor.run(args.league, args.season, args.limit)
    
    # Return exit code based on errors
    sys.exit(1 if stats['errors'] > 0 else 0)


if __name__ == "__main__":
    main()
