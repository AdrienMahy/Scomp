"""Monitoring dashboard for scraping automation"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.config.database import SessionLocal
from ..models import ScrapingTask

logger = logging.getLogger(__name__)


class ScrapingMonitor:
    """Monitor and analyze scraping automation logs"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
    
    def get_recent_scrapes(self, limit: int = 20) -> List[Dict]:
        """Get recent scraping activities"""
        logs = self.db.query(ScrapingTask).order_by(
            desc(ScrapingTask.created_at)
        ).limit(limit).all()
        
        return [{
            "id": log.id,
            "competition_id": log.competition_id,
            "status": log.status,
            "games_count": log.processed_items,
            "error_message": log.error_message,
            "executed_at": log.created_at,
        } for log in logs]
    
    def get_statistics(self, hours: int = 24) -> Dict:
        """Get scraping statistics for the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        logs = self.db.query(ScrapingTask).filter(
            ScrapingTask.created_at >= cutoff_time
        ).all()
        
        total = len(logs)
        successful = len([l for l in logs if l.status == "success"])
        errors = len([l for l in logs if l.status == "error"])
        total_games = sum(l.processed_items or 0 for l in logs)
        
        return {
            "period_hours": hours,
            "total_scrapes": total,
            "successful": successful,
            "failed": errors,
            "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "N/A",
            "total_games_processed": total_games,
            "avg_games_per_scrape": f"{(total_games/total):.1f}" if total > 0 else "N/A",
        }
    
    def get_competition_stats(self) -> Dict[str, Dict]:
        """Get statistics per competition"""
        competitions = self.db.query(ScrapingTask.competition_id).distinct().all()
        
        stats = {}
        for (comp_id,) in competitions:
            logs = self.db.query(ScrapingTask).filter(
                ScrapingTask.competition_id == comp_id
            ).all()
            
            successful = len([l for l in logs if l.status == "success"])
            errors = len([l for l in logs if l.status == "error"])
            
            stats[comp_id] = {
                "total_scrapes": len(logs),
                "successful": successful,
                "failed": errors,
                "success_rate": f"{(successful/len(logs)*100):.1f}%" if logs else "N/A",
            }
        
        return stats
    
    def get_latest_error(self) -> Dict:
        """Get the latest error (if any)"""
        log = self.db.query(ScrapingTask).filter(
            ScrapingTask.status.in_(["failed", "partial"])
        ).order_by(desc(ScrapingTask.created_at)).first()
        
        if not log:
            return {"status": "No errors"}
        
        return {
            "competition_id": log.competition_id,
            "error_message": log.error_message,
            "executed_at": log.created_at,
            "ago": str(datetime.utcnow() - log.created_at),
        }
    
    def print_dashboard(self):
        """Print a text-based monitoring dashboard"""
        print("\n" + "="*80)
        print("📊 SCOMP SCRAPING AUTOMATION - MONITORING DASHBOARD")
        print("="*80)
        
        # Statistics
        print("\n📈 STATISTICS (Last 24 Hours)")
        print("-" * 80)
        stats = self.get_statistics(hours=24)
        print(f"  Total Scrapes: {stats['total_scrapes']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Success Rate: {stats['success_rate']}")
        print(f"  Total Games Processed: {stats['total_games_processed']}")
        print(f"  Avg Games/Scrape: {stats['avg_games_per_scrape']}")
        
        # Competition stats
        print("\n🏆 COMPETITIONS")
        print("-" * 80)
        comp_stats = self.get_competition_stats()
        if comp_stats:
            for comp_id, comp_data in comp_stats.items():
                print(f"  {comp_id}")
                print(f"    Total: {comp_data['total_scrapes']} | Success: {comp_data['successful']} | Failed: {comp_data['failed']} | Rate: {comp_data['success_rate']}")
        else:
            print("  No scraping data yet")
        
        # Recent activity
        print("\n🔄 RECENT ACTIVITY (Last 10)")
        print("-" * 80)
        recent = self.get_recent_scrapes(limit=10)
        if recent:
            for log in recent:
                status_icon = "✓" if log['status'] == "success" else "✗"
                print(f"  {status_icon} [{log['executed_at']}] {log['competition_id']} - {log['games_count']} games")
                if log['error_message']:
                    print(f"    Error: {log['error_message'][:60]}...")
        else:
            print("  No recent scrapes")
        
        # Latest error
        print("\n⚠️  LATEST ERROR")
        print("-" * 80)
        latest_error = self.get_latest_error()
        if "status" in latest_error:
            print(f"  {latest_error['status']}")
        else:
            print(f"  Competition: {latest_error['competition_id']}")
            print(f"  Message: {latest_error['error_message']}")
            print(f"  When: {latest_error['ago']} ago")
        
        print("\n" + "="*80)
        print(f"Generated: {datetime.utcnow()}")
        print("="*80 + "\n")
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()


def main():
    """Simple CLI for monitoring dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scomp Scraping Automation Monitor")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back for stats (default: 24)")
    parser.add_argument("--competition", help="Filter by competition ID")
    
    args = parser.parse_args()
    
    monitor = ScrapingMonitor()
    
    try:
        if args.competition:
            # Filter mode
            print(f"\n📊 Stats for competition: {args.competition}")
            logs = monitor.db.query(ScrapingTask).filter(
                ScrapingTask.competition_id == args.competition
            ).order_by(desc(ScrapingTask.created_at)).limit(20).all()
            
            for log in logs:
                status = "✓" if log.status == "success" else "✗"
                print(f"  {status} [{log.created_at}] {log.processed_items} games")
                if log.error_message:
                    print(f"     Error: {log.error_message}")
        else:
            # Dashboard mode
            monitor.print_dashboard()
    
    finally:
        monitor.close()


if __name__ == "__main__":
    main()
