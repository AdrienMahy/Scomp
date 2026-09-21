"""Smart scraper - Automatically detects and scrapes relevant games"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .scheduler_config import AutomationConfig
from ..config.database import SessionLocal
from ..models import Game, Competition
from ..orchestration.scrape_workflows import scrape_autonomous

logger = logging.getLogger(__name__)


class SmartScraper:
    """
    Intelligent scraper that detects games matching criteria and scrapes them.
    
    Criteria:
    - Within configured time window (e.g., 7 days ahead, 1 day back)
    - Status: scheduled, live, or finished within time window
    - For enabled competitions
    """
    
    def __init__(self):
        self.config = AutomationConfig
    
    def run(self) -> Dict[str, Any]:
        """
        Execute smart scraping cycle (synchronous wrapper)
        Runs the async scrape in an event loop
        
        Returns:
            {
                "status": "success|partial|failed",
                "competitions_scraped": int,
                "games_checked": int,
                "games_updated": int,
                "errors": List[str],
                "duration_seconds": float
            }
        """
        # Run async method in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.run_async())
    
    async def run_async(self) -> Dict[str, Any]:
        """
        Execute smart scraping cycle (asynchronous)
        
        Returns:
            {
                "status": "success|partial|failed",
                "competitions_scraped": int,
                "games_checked": int,
                "games_updated": int,
                "errors": List[str],
                "duration_seconds": float
            }
        """
        start_time = datetime.utcnow()
        db = SessionLocal()
        result = {
            "status": "success",
            "competitions_scraped": 0,
            "games_checked": 0,
            "games_updated": 0,
            "errors": [],
            "duration_seconds": 0
        }
        
        try:
            logger.info("=" * 60)
            logger.info("🤖 Smart Scraping Cycle Started")
            logger.info("=" * 60)
            
            # Get active competitions
            active_comps = self.config.get_active_competitions()
            if not active_comps:
                logger.warning("No active competitions configured for scraping")
                result["status"] = "failed"
                result["errors"].append("No active competitions configured")
                return result
            
            logger.info(f"Active competitions: {len(active_comps)}")
            for comp in active_comps:
                logger.info(f"  - {comp['name']} (provider: {comp['provider']})")
            
            # The autonomous workflow compares the provider response with the DB.
            for comp in active_comps:
                comp_id = comp["id"]
                try:
                    logger.info(f"\nScraping competition {comp_id}")
                    scrape_result = await scrape_autonomous(
                        db=db,
                        competition_id=comp_id,
                        season_id=str(comp["season_id"]),
                    )
                    
                    result["competitions_scraped"] += 1
                    result["games_checked"] += scrape_result.get("detected_count", 0)
                    result["games_updated"] += scrape_result.get("processed_count", 0)
                    
                    logger.info(f"✓ Competition {comp_id} scraped successfully")
                    logger.info(f"  Games processed: {len(scrape_result) if scrape_result else 0}")
                    
                except Exception as e:
                    error_msg = f"Failed to scrape competition {comp_id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)
                    result["status"] = "partial"
                    
            
            if result["errors"]:
                result["status"] = "partial" if result["competitions_scraped"] > 0 else "failed"
            
        except Exception as e:
            logger.error(f"Smart scraping cycle failed: {str(e)}", exc_info=True)
            result["status"] = "failed"
            result["errors"].append(str(e))
        
        finally:
            # Calculate duration
            result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
            
            # Log summary
            logger.info("=" * 60)
            logger.info("📊 Smart Scraping Cycle Summary")
            logger.info(f"Status: {result['status'].upper()}")
            logger.info(f"Competitions scraped: {result['competitions_scraped']}")
            logger.info(f"Games checked: {result['games_checked']}")
            logger.info(f"Games updated: {result['games_updated']}")
            if result["errors"]:
                logger.info(f"Errors: {len(result['errors'])}")
                for err in result["errors"]:
                    logger.info(f"  - {err}")
            logger.info(f"Duration: {result['duration_seconds']:.1f}s")
            logger.info("=" * 60)
            
            db.close()
        
        return result
    
    def _get_matching_games(self, db: Session, active_comps: List[Dict]) -> List[Dict]:
        """
        Get games matching scraping criteria:
        - In active competitions
        - Within time window
        - Status: scheduled, live, or finished (within window)
        """
        time_from, time_to = self.config.get_time_window()
        comp_ids = [c["id"] for c in active_comps]
        
        logger.debug(f"Time window: {time_from} to {time_to}")
        logger.debug(f"Competition IDs: {comp_ids}")
        
        # Query games
        games = db.query(Game).filter(
            and_(
                Game.competition_id.in_(comp_ids),
                Game.starts_at.between(time_from, time_to)
            )
        ).all()
        
        return [{
            "id": g.id,
            "name": g.name,
            "competition_id": g.competition_id,
            "starts_at": g.starts_at,
            "status": g.status
        } for g in games]
    
    def _group_by_competition(self, games: List[Dict]) -> Dict[str, List[Dict]]:
        """Group games by competition ID"""
        grouped = {}
        for game in games:
            comp_id = game["competition_id"]
            if comp_id not in grouped:
                grouped[comp_id] = []
            grouped[comp_id].append(game)
        return grouped
    
