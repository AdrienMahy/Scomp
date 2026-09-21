"""Test and debug script for smart scraper automation"""
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from backend.src.automation import SmartScraper
from backend.src.automation.scheduler_config import AutomationConfig
from backend.src.config.database import SessionLocal
from backend.src.models import Competition, Game
from sqlalchemy import func

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_config():
    """Print current automation configuration"""
    print_header("📋 AUTOMATION CONFIGURATION")
    
    print(f"Scrape Interval: {AutomationConfig.SCRAPE_INTERVAL} minutes")
    print(f"Live Game Window: {AutomationConfig.LIVE_GAME_WINDOW} minutes")
    print(f"Max Concurrent Scrapes: {AutomationConfig.MAX_CONCURRENT_SCRAPES}")
    print(f"Task Timeout: {AutomationConfig.TASK_TIMEOUT} seconds")
    print(f"Logging Enabled: {AutomationConfig.ENABLE_SCRAPE_LOGGING}")
    
    print(f"\nActive Competitions:")
    active = AutomationConfig.get_active_competitions()
    if not active:
        print("  ⚠️  No active competitions configured!")
    else:
        for comp in active:
            print(f"  ✓ {comp['name']} (ID: {comp['id']})")
            print(f"    - Provider: {comp['provider']}")
            print(f"    - Look ahead: {comp['look_ahead_days']} days")
            print(f"    - Look back: {comp['look_back_days']} days")
    
    # Show time window
    time_from, time_to = AutomationConfig.get_time_window()
    print(f"\nTime Window for Matching Games:")
    print(f"  From: {time_from}")
    print(f"  To:   {time_to}")

def print_database_stats():
    """Print database statistics"""
    print_header("📊 DATABASE STATISTICS")
    
    db = SessionLocal()
    try:
        # Competition count
        comp_count = db.query(func.count(Competition.id)).scalar()
        print(f"Total Competitions: {comp_count}")
        
        # Games by competition
        comp_games = db.query(
            Competition.name,
            func.count(Game.id).label('game_count')
        ).outerjoin(Game).group_by(Competition.id, Competition.name).all()
        
        print("\nGames by Competition:")
        total_games = 0
        for comp_name, game_count in comp_games:
            print(f"  - {comp_name}: {game_count} games")
            total_games += game_count
        
        print(f"\nTotal Games: {total_games}")
        
        # Games by status
        print("\nGames by Status:")
        from sqlalchemy import text
        status_counts = db.query(Game.status, func.count(Game.id)).group_by(Game.status).all()
        for status, count in status_counts:
            print(f"  - {status}: {count} games")
            
    finally:
        db.close()

def test_game_detection():
    """Test game detection logic"""
    print_header("🎯 TESTING GAME DETECTION")
    
    db = SessionLocal()
    scraper = SmartScraper()
    
    try:
        # Get active competitions
        active_comps = AutomationConfig.get_active_competitions()
        
        if not active_comps:
            print("⚠️  No active competitions configured!")
            return
        
        print(f"Testing with {len(active_comps)} active competition(s)...\n")
        
        # Get matching games
        matching_games = scraper._get_matching_games(db, active_comps)
        
        print(f"Found {len(matching_games)} games matching criteria:")
        
        if matching_games:
            # Group by competition
            by_comp = scraper._group_by_competition(matching_games)
            for comp_id, games in by_comp.items():
                print(f"\n  Competition: {comp_id}")
                print(f"  Games: {len(games)}")
                for game in games[:3]:  # Show first 3
                    print(f"    - {game['name']}")
                    print(f"      Status: {game['status']}")
                    print(f"      Starts: {game['starts_at']}")
                if len(games) > 3:
                    print(f"    ... and {len(games) - 3} more")
        else:
            print("  ℹ️  No games found in time window")
            
    finally:
        db.close()

def run_smart_scraper_test():
    """Run a complete smart scraper cycle (TEST MODE)"""
    print_header("🤖 RUNNING SMART SCRAPER TEST")
    
    print("⚠️  This will execute a REAL scraping cycle if games are found.")
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("Cancelled.")
        return
    
    scraper = SmartScraper()
    result = scraper.run()
    
    print_header("✅ SMART SCRAPER TEST COMPLETE")
    print(f"Status: {result['status'].upper()}")
    print(f"Competitions Scraped: {result['competitions_scraped']}")
    print(f"Games Checked: {result['games_checked']}")
    print(f"Games Updated: {result['games_updated']}")
    print(f"Duration: {result['duration_seconds']:.1f}s")
    
    if result['errors']:
        print(f"\n❌ Errors ({len(result['errors'])}):")
        for err in result['errors']:
            print(f"  - {err}")

def main():
    """Main menu"""
    while True:
        print_header("🔧 SCOMP AUTOMATION TEST SUITE")
        print("1. View Configuration")
        print("2. View Database Statistics")
        print("3. Test Game Detection")
        print("4. Run Smart Scraper Cycle (REAL)")
        print("5. Exit")
        
        choice = input("\nSelect an option (1-5): ").strip()
        
        if choice == "1":
            print_config()
        elif choice == "2":
            print_database_stats()
        elif choice == "3":
            test_game_detection()
        elif choice == "4":
            run_smart_scraper_test()
        elif choice == "5":
            print("\n✅ Goodbye!")
            break
        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
