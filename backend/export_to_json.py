#!/usr/bin/env python3
"""
Export game data from database to JSON with nested data structure preserved
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add backend to path
sys.path.insert(0, str(Path.cwd()))

from src.config.database import SessionLocal
from src.SportsDynamics.models.game import Game


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime and Decimal objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, )):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def extract_game_data(game):
    """Extract game data with all nested structures"""
    
    # Build structured output with nested data
    export_data = {
        "game": {
            "id": game.id,
            "name": game.name,
            "result": game.result,
            "home_score": game.home_score,
            "away_score": game.away_score,
            "home_team_id": game.home_team_id,
            "away_team_id": game.away_team_id,
            "round_name": game.round_name,
            "starts_at": str(game.starts_at),
            "played_at": str(game.played_at),
            "created_at": str(game.created_at),
            "updated_at": str(game.updated_at),
        },
        "squads": [],
        "players": [],
        "output_files": [],
        "providers": [],
    }
    
    # Extract squads and players
    if game.raw_data and 'squads' in game.raw_data:
        squads_data = game.raw_data['squads']
        squads_list = squads_data if isinstance(squads_data, list) else squads_data.get('items', [])
        
        squad_names = ["Home", "Away"]
        
        for squad_idx, squad in enumerate(squads_list):
            team_id = squad.get('teamId', 'N/A')
            
            # Add squad info
            export_data["squads"].append({
                "squad_number": squad_idx + 1,
                "squad_type": squad_names[squad_idx] if squad_idx < len(squad_names) else f"Squad {squad_idx}",
                "team_id": team_id,
                "player_count": 0,
            })
            
            # Extract players from this squad
            players_data = squad.get('players', {})
            players_list = players_data if isinstance(players_data, list) else players_data.get('items', [])
            
            for player in players_list:
                player_info = player.get('player', {})
                export_data["players"].append({
                    "squad_type": squad_names[squad_idx] if squad_idx < len(squad_names) else f"Squad {squad_idx}",
                    "team_id": team_id,
                    "player_id": player_info.get('id', 'N/A'),
                    "first_name": player_info.get('firstName', 'N/A'),
                    "last_name": player_info.get('lastName', 'N/A'),
                    "jersey_number": player.get('jerseyNumber', 'N/A'),
                    "is_starting": player.get('isStarting', False),
                    "is_captain": player.get('isCaptain', False),
                })
            
            # Update player count
            export_data["squads"][squad_idx]["player_count"] = len(players_list)
    
    # Extract output files
    if game.raw_data and 'outputFiles' in game.raw_data:
        output_files_data = game.raw_data['outputFiles']
        files_list = output_files_data if isinstance(output_files_data, list) else output_files_data.get('items', [])
        
        for file_obj in files_list:
            file_info = file_obj.get('file', {})
            export_data["output_files"].append({
                "file_id": file_info.get('id', 'N/A'),
                "file_name": file_obj.get('fileName', 'N/A'),
                "file_type": file_info.get('fileType', 'N/A'),
                "size_bytes": file_info.get('size', 0),
                "url": file_info.get('url', 'N/A'),
            })
    
    # Extract providers
    if game.raw_data and 'providers' in game.raw_data:
        providers_data = game.raw_data['providers']
        providers_list = providers_data if isinstance(providers_data, list) else providers_data.get('items', [])
        
        for provider in providers_list:
            provider_info = provider.get('provider', {})
            export_data["providers"].append({
                "provider_id": provider_info.get('id', 'N/A'),
                "provider_name": provider_info.get('name', 'N/A'),
                "external_id": provider.get('externalId', 'N/A'),
            })
    
    return export_data


def main():
    """Main export function"""
    # Get database session
    db = SessionLocal()
    
    # Get first game from database
    game = db.query(Game).first()
    
    if not game:
        print("❌ No games found in database")
        db.close()
        return
    
    print(f"✅ Found game: {game.name}")
    print(f"📦 Exporting to JSON with nested data...\n")
    
    # Extract data
    export_data = extract_game_data(game)
    
    # Save file
    output_path = Path(__file__).parent.parent / "start" / "GAME_ARCHITECTURE_EXPORT.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, cls=DateTimeEncoder)
    
    file_size = output_path.stat().st_size
    print(f"✅ JSON file created: {output_path}")
    print(f"📁 File size: {file_size / 1024:.1f} KB")
    print(f"\n📊 STRUCTURE OVERVIEW:")
    print(f"   - Game: 1 record")
    print(f"   - Squads: {len(export_data['squads'])} records")
    print(f"   - Players: {len(export_data['players'])} records")
    print(f"   - Output Files: {len(export_data['output_files'])} records")
    print(f"   - Providers: {len(export_data['providers'])} records")
    
    db.close()


if __name__ == "__main__":
    main()
