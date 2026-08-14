#!/usr/bin/env python3
"""
SportsDynamics API Integration Guide
Documents the API structure and test queries
"""
import json
import sys
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Load environment
from dotenv import load_dotenv
env_file = project_root / "start" / ".env"
load_dotenv(env_file)

from src.api import SportsDynamicsClient
from src.config.settings import get_settings

settings = get_settings()

# Create output directory
output_dir = project_root / "test_outputs"
output_dir.mkdir(exist_ok=True)

print("\n" + "="*70)
print("SPORTSDYNAMICS API INTEGRATION GUIDE")
print("="*70)

# 1. Show configuration
print("\n📋 API CONFIGURATION")
print("-" * 70)
print(f"API URL: {settings.sportsdynamics.api_url}")
print(f"API Key: {settings.sportsdynamics.api_key[:20]}... (hidden for security)")
print(f"Auth Header: X-API-Key")
print(f"Content-Type: application/json")

# 2. Load ID.json
print("\n📊 COMPETITIONS LOADED FROM ID.json")
print("-" * 70)
try:
    id_config = settings.load_ids_config()
    
    for provider in id_config:
        provider_name = provider.get("Provider")
        leagues = provider.get("Leagues", [])
        print(f"\n🏢 Provider: {provider_name}")
        
        for league in leagues:
            league_name = league.get("Name")
            comp_id = league.get("competitionId")
            seasons = league.get("Seasons", [])
            print(f"  ⚽ League: {league_name}")
            print(f"     Competition ID: {comp_id}")
            print(f"     Seasons: {len(seasons)}")
            
            for season in seasons:
                season_name = season.get("name")
                season_id = season.get("gameGroupId") or season.get("seasonId")
                print(f"       📅 {season_name}: {season_id}")
    
    # Save loaded config
    with open(output_dir / "loaded_configuration.json", 'w') as f:
        json.dump({
            "api_url": settings.sportsdynamics.api_url,
            "auth_header": "X-API-Key",
            "competitions": id_config
        }, f, indent=2)
    
    print(f"\n✅ Saved configuration to {output_dir / 'loaded_configuration.json'}")
    
except Exception as e:
    print(f"❌ Error loading ID.json: {e}")
    sys.exit(1)

# 3. Show GraphQL query examples
print("\n\n📝 GRAPHQL QUERY EXAMPLES")
print("-" * 70)

queries_doc = {
    "get_competitions": {
        "description": "Fetch all available competitions",
        "query": """
query getCompetitions($pagination: PaginationInput) {
    getCompetitions(pagination: $pagination) {
        meta { count pageCount currentPage }
        items {
            id
            name
            seasons { items { id name season } }
        }
    }
}
        """,
        "variables": {"pagination": {"limit": 100, "page": 1}}
    },
    "get_seasons": {
        "description": "Fetch seasons for a competition",
        "query": """
query getSeasons($filters: [SeasonFilter!], $pagination: PaginationInput) {
    getSeasons(filters: $filters, pagination: $pagination) {
        meta { count pageCount currentPage }
        items {
            id
            name
            season
            stages { items { id name type } }
        }
    }
}
        """,
        "variables": {
            "filters": [{"competition": {"id": {"equals": "COMPETITION_ID_HERE"}}}],
            "pagination": {"limit": 100, "page": 1}
        }
    },
    "get_games": {
        "description": "Fetch games for a season",
        "query": """
query getGames($filters: [GameFilter!], $pagination: PaginationInput) {
    getGames(filters: $filters, pagination: $pagination) {
        items {
            id
            name
            result
            startsAt
            playedAt
            round { name }
            homeScore
            awayScore
            homeTeamFormation
            awayTeamFormation
            homeTeam { id brand }
            awayTeam { id brand }
            gameOutputFiles { items { id name fileName } }
            periods { id periodId periodStartTime periodEndTime }
            squads { 
                teamId 
                players { items { 
                    id isStarting isCaptain jerseyNumber 
                    player { id firstName lastName name usageName } 
                } }
            }
            providers { items { id externalId provider { id name } } }
        }
    }
}
        """,
        "variables": {
            "filters": [{"available": {"equals": True}}],
            "pagination": {"limit": 10, "page": 1}
        }
    },
    "get_clubs": {
        "description": "Fetch all clubs",
        "query": """
query getClubs($pagination: PaginationInput) {
    getClubs(pagination: $pagination) {
        meta { count pageCount currentPage }
        items {
            id
            brand
            logoUrl
            games { items { id name } }
            providers { items { externalId provider { name } } }
        }
    }
}
        """,
        "variables": {"pagination": {"limit": 100, "page": 1}}
    }
}

for query_name, query_info in queries_doc.items():
    print(f"\n🔹 {query_name.upper()}")
    print(f"   Description: {query_info['description']}")
    print(f"   Variables: {json.dumps(query_info['variables'], indent=6)}")

# Save queries reference
with open(output_dir / "graphql_queries.json", 'w') as f:
    json.dump(queries_doc, f, indent=2, default=str)

print(f"\n✅ Saved GraphQL queries reference to {output_dir / 'graphql_queries.json'}")

# 4. Test API connectivity
print("\n\n🧪 API CONNECTIVITY TEST")
print("-" * 70)

try:
    import requests
    from datetime import datetime
    
    client = SportsDynamicsClient()
    
    print(f"Testing basic connectivity to {settings.sportsdynamics.api_url}...")
    
    # Simple test query
    test_query = """
    query {
        __typename
    }
    """
    
    response = requests.post(
        client.api_url,
        json={"query": test_query},
        headers=client.headers,
        timeout=10
    )
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ API is accessible!")
        data = response.json()
        if "errors" not in data:
            print(f"✅ GraphQL query successful")
            # Save successful response
            with open(output_dir / "api_connectivity_test.json", 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "status_code": response.status_code,
                    "response": data
                }, f, indent=2)
        else:
            print(f"⚠️ GraphQL errors: {data['errors']}")
    elif response.status_code == 504:
        print("⚠️ API returned 504 Gateway Timeout")
        print("   → Server may be temporarily unavailable")
        print("   → Try again later")
    elif response.status_code == 403:
        print("❌ API returned 403 Forbidden")
        print("   → Check API key is correct")
        print("   → Check authentication header format")
    else:
        print(f"⚠️ Unexpected status code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

except requests.exceptions.Timeout:
    print("❌ Connection timeout")
    print("   → API server may be slow or unreachable")
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection error: {e}")
    print("   → Check network connectivity")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("NEXT STEPS:")
print("-" * 70)
print("1. If API is accessible:")
print("   → Run: python3 test_api_full.py")
print("2. If API is down:")
print("   → Check API status/documentation")
print("   → Verify API key and credentials")
print("3. Review generated files:")
print(f"   → {output_dir / 'loaded_configuration.json'}")
print(f"   → {output_dir / 'graphql_queries.json'}")
print("="*70 + "\n")
