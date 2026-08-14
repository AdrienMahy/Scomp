#!/usr/bin/env python3
"""
Test script for SportsDynamics API
Tests all endpoints with real credentials and saves responses
"""
import json
import sys
from pathlib import Path
from datetime import datetime
import os

# Add backend to path
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Load environment from start/.env BEFORE importing anything from src
from dotenv import load_dotenv
env_file = project_root / "start" / ".env"
print(f"Loading .env from: {env_file}")
load_dotenv(env_file)

# Now import after .env is loaded
from src.api import SportsDynamicsClient
from src.config.settings import get_settings

settings = get_settings()

# Create output directory
output_dir = project_root / "test_outputs"
output_dir.mkdir(exist_ok=True)

def save_response(name: str, data: dict):
    """Save response to JSON file"""
    filepath = output_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"✅ Saved to {filepath}")
    return filepath

def test_competitions():
    """Test getCompetitions endpoint"""
    print("\n" + "="*60)
    print("TEST: getCompetitions()")
    print("="*60)
    
    try:
        client = SportsDynamicsClient()
        result = client.get_competitions()
        
        print(f"✅ Got {len(result)} competitions")
        
        if result:
            print(f"\n📊 First competition:")
            first = result[0]
            print(f"  ID: {first.get('id')}")
            print(f"  Name: {first.get('name')}")
            seasons = first.get('seasons', {}).get('items', [])
            print(f"  Seasons: {len(seasons)}")
            
            if seasons:
                print(f"    First season: {seasons[0]}")
        
        # Save full response
        save_response("getCompetitions", {"items": result})
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_seasons(competition_id: str):
    """Test getSeasons endpoint"""
    print("\n" + "="*60)
    print(f"TEST: getSeasons({competition_id})")
    print("="*60)
    
    try:
        client = SportsDynamicsClient()
        result = client.get_seasons(competition_id)
        
        print(f"✅ Got {len(result)} seasons")
        
        if result:
            print(f"\n📊 First season:")
            first = result[0]
            print(f"  ID: {first.get('id')}")
            print(f"  Name: {first.get('name')}")
            print(f"  Season year: {first.get('season')}")
            stages = first.get('stages', {}).get('items', [])
            print(f"  Stages: {len(stages)}")
            
            if stages:
                print(f"    Stages: {stages}")
        
        # Save full response
        save_response("getSeasons", {"items": result})
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_games(competition_id: str, season_id: str = None, limit: int = 5):
    """Test getGames endpoint"""
    print("\n" + "="*60)
    print(f"TEST: getGames(competition_id={competition_id}, season_id={season_id}, limit={limit})")
    print("="*60)
    
    try:
        client = SportsDynamicsClient()
        result = client.get_games(competition_id, season_id, limit=limit)
        
        print(f"✅ Got {len(result)} games (limit={limit})")
        
        if result:
            print(f"\n📊 First game structure:")
            first = result[0]
            
            print(f"  id: {first.get('id')}")
            print(f"  name: {first.get('name')}")
            print(f"  result: {first.get('result')}")
            
            print(f"\n  🏠 Home Team:")
            home = first.get('homeTeam', {})
            print(f"    ID: {home.get('id')}")
            print(f"    Brand: {home.get('brand')}")
            
            print(f"\n  🏁 Away Team:")
            away = first.get('awayTeam', {})
            print(f"    ID: {away.get('id')}")
            print(f"    Brand: {away.get('brand')}")
            
            print(f"\n  📊 Scores:")
            print(f"    Home: {first.get('homeScore')}")
            print(f"    Away: {first.get('awayScore')}")
            print(f"    Formation Home: {first.get('homeTeamFormation')}")
            print(f"    Formation Away: {first.get('awayTeamFormation')}")
            
            print(f"\n  📅 Dates:")
            print(f"    Starts at: {first.get('startsAt')}")
            print(f"    Played at: {first.get('playedAt')}")
            print(f"    Round: {first.get('round', {}).get('name')}")
            
            print(f"\n  🎥 Game Output Files:")
            files = first.get('gameOutputFiles', {}).get('items', [])
            print(f"    Count: {len(files)}")
            if files:
                print(f"    First file: {files[0]}")
            
            print(f"\n  ⏱️ Periods:")
            periods = first.get('periods', [])
            print(f"    Count: {len(periods)}")
            if periods:
                print(f"    First period: {periods[0]}")
            
            print(f"\n  👥 Squads:")
            squads = first.get('squads', [])
            print(f"    Count: {len(squads)}")
            if squads:
                squad = squads[0]
                print(f"    Team ID: {squad.get('teamId')}")
                players = squad.get('players', {}).get('items', [])
                print(f"    Players: {len(players)}")
                if players:
                    player = players[0]
                    print(f"      First player:")
                    print(f"        ID: {player.get('id')}")
                    print(f"        Name: {player.get('player', {}).get('name')}")
                    print(f"        Jersey: {player.get('jerseyNumber')}")
                    print(f"        Starting: {player.get('isStarting')}")
                    print(f"        Captain: {player.get('isCaptain')}")
            
            print(f"\n  🔗 Providers:")
            providers = first.get('providers', {}).get('items', [])
            print(f"    Count: {len(providers)}")
            if providers:
                print(f"    Providers: {providers}")
        
        # Save full response
        save_response("getGames", {"items": result})
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_clubs():
    """Test getClubs endpoint"""
    print("\n" + "="*60)
    print("TEST: getClubs()")
    print("="*60)
    
    try:
        client = SportsDynamicsClient()
        result = client.get_clubs()
        
        print(f"✅ Got {len(result)} clubs")
        
        if result:
            print(f"\n📊 First club:")
            first = result[0]
            print(f"  ID: {first.get('id')}")
            print(f"  Brand: {first.get('brand')}")
            print(f"  Logo URL: {first.get('logoUrl')}")
            
            games = first.get('games', {}).get('items', [])
            print(f"  Games: {len(games)}")
            
            providers = first.get('providers', {}).get('items', [])
            print(f"  Providers: {len(providers)}")
            if providers:
                print(f"    First provider: {providers[0]}")
        
        # Save full response
        save_response("getClubs", {"items": result})
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run all tests"""
    print("\n" + "🚀 "*30)
    print("SPORTSDYNAMICS API TEST SUITE")
    print("🚀 "*30)
    
    print(f"\nAPI Key: {settings.sportsdynamics.api_key[:10]}...")
    print(f"API URL: {settings.sportsdynamics.api_url}")
    print(f"Output directory: {output_dir}")
    
    # Load ID.json for competition IDs
    id_config = settings.load_ids_config()
    
    # Test 1: Get all competitions
    competitions = test_competitions()
    
    if not competitions:
        print("\n❌ Failed to get competitions. Aborting other tests.")
        return
    
    # Test 2: Get seasons for first competition
    if competitions:
        first_comp_id = competitions[0].get('id')
        print(f"\n\nUsing first competition: {first_comp_id}")
        seasons = test_seasons(first_comp_id)
        
        # Test 3: Get games for first competition/season
        if seasons:
            first_season_id = seasons[0].get('id')
            print(f"\nUsing first season: {first_season_id}")
            games = test_games(first_comp_id, first_season_id, limit=3)
    
    # Test 4: Get all clubs
    clubs = test_clubs()
    
    print("\n" + "✅ "*30)
    print("ALL TESTS COMPLETED")
    print("Check test_outputs/ for detailed JSON responses")
    print("✅ "*30)

if __name__ == "__main__":
    main()
