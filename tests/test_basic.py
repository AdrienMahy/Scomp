#!/usr/bin/env python3
"""
Basic SportsDynamics API Test
1. Load credentials from .env
2. Load query from graphql_queries.json
3. Build GraphQL filter
4. Send request with proper headers
5. Display response
"""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os
import requests

# Setup paths
project_root = Path(__file__).parent
env_file = project_root / "start" / ".env"
queries_file = project_root / "test_outputs" / "graphql_queries.json"

print("\n" + "="*70)
print("BASIC SPORTSDYNAMICS API TEST")
print("="*70)

# 1️⃣ LOAD CREDENTIALS
print("\n1️⃣ LOADING CREDENTIALS")
print("-" * 70)
load_dotenv(env_file)

api_key = os.getenv("SPORTSDYNAMICS_API_KEY")
api_url = "https://api-v2.sportsdynamics.eu/graphql"

if not api_key:
    print("❌ API Key not found in .env")
    sys.exit(1)

print(f"✅ API Key loaded: {api_key[:20]}...")
print(f"✅ API URL: {api_url}")

# 2️⃣ LOAD QUERY
print("\n2️⃣ LOADING GRAPHQL QUERY")
print("-" * 70)

if not queries_file.exists():
    print(f"❌ Queries file not found: {queries_file}")
    print("   Run test_api_discovery.py first to generate it")
    sys.exit(1)

with open(queries_file, 'r') as f:
    queries = json.load(f)

# Get competitions query
comp_query_data = queries.get("get_competitions")
if not comp_query_data:
    print("❌ get_competitions query not found")
    sys.exit(1)

query_string = comp_query_data["query"].strip()
variables = comp_query_data["variables"]

print("✅ Loaded 'get_competitions' query")
print(f"   Variables: {json.dumps(variables)}")

# 3️⃣ BUILD GRAPHQL FILTER
print("\n3️⃣ BUILDING GRAPHQL PAYLOAD")
print("-" * 70)

payload = {
    "query": query_string,
    "variables": variables
}

print("Payload structure:")
print(f"  - Query: {query_string[:100]}...")
print(f"  - Variables: {json.dumps(variables, indent=4)}")

# 4️⃣ CREATE REQUEST WITH HEADERS
print("\n4️⃣ SETTING UP REQUEST HEADERS")
print("-" * 70)

headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

print("Headers:")
print(f"  X-API-Key: {api_key[:20]}... (hidden)")
print(f"  Content-Type: application/json")

# 5️⃣ SEND REQUEST TO API
print("\n5️⃣ SENDING REQUEST TO API")
print("-" * 70)

try:
    print(f"POST {api_url}")
    response = requests.post(
        api_url,
        json=payload,
        headers=headers,
        timeout=30
    )
    
    print(f"✅ Response received")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ HTTP 200 OK")
        
        data = response.json()
        
        # Check for GraphQL errors
        if "errors" in data:
            print("\n❌ GraphQL Errors:")
            for error in data["errors"]:
                print(f"   - {error}")
        elif "data" in data:
            print("✅ Valid GraphQL response received")
            
            # Extract competitions
            competitions = data.get("data", {}).get("getCompetitions", {}).get("items", [])
            
            print(f"\n📊 RESPONSE DATA")
            print("-" * 70)
            print(f"✅ Found {len(competitions)} competitions")
            
            if competitions:
                print(f"\n🏢 First competition:")
                comp = competitions[0]
                print(f"   ID: {comp.get('id')}")
                print(f"   Name: {comp.get('name')}")
                
                seasons = comp.get("seasons", {}).get("items", [])
                print(f"   Seasons: {len(seasons)}")
                
                if seasons:
                    print(f"\n   First season:")
                    season = seasons[0]
                    print(f"     ID: {season.get('id')}")
                    print(f"     Name: {season.get('name')}")
                    print(f"     Season Year: {season.get('season')}")
            
            # Save response
            output_file = project_root / "test_outputs" / "api_response_competitions.json"
            output_file.parent.mkdir(exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"\n✅ Full response saved to: {output_file}")
        else:
            print("⚠️ Unexpected response structure")
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
    
    elif response.status_code == 403:
        print("❌ 403 Forbidden")
        print("   Check if API key is valid")
        print(f"   Response: {response.text[:200]}")
    
    elif response.status_code == 504:
        print("⚠️ 504 Gateway Timeout")
        print("   API server may be temporarily unavailable")
        print("   Try again later")
    
    else:
        print(f"⚠️ Unexpected status code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

except requests.exceptions.Timeout:
    print("❌ Request Timeout (30 seconds)")
    print("   API server is not responding")
    
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: {e}")
    print("   Check network connectivity")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")
