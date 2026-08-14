#!/usr/bin/env python3
"""
Test different GraphQL queries to find which ones work
"""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os
import requests

project_root = Path(__file__).parent
env_file = project_root / "start" / ".env"
queries_file = project_root / "test_outputs" / "graphql_queries.json"

load_dotenv(env_file)
api_key = os.getenv("SPORTSDYNAMICS_API_KEY")
api_url = "https://api-v2.sportsdynamics.eu/graphql"

print("\n" + "="*70)
print("TESTING ALL GRAPHQL QUERIES")
print("="*70 + "\n")

# Load queries
with open(queries_file, 'r') as f:
    all_queries = json.load(f)

headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

# Test each query
for query_name, query_data in all_queries.items():
    print(f"\n{'='*70}")
    print(f"Testing: {query_name.upper()}")
    print(f"{'='*70}")
    print(f"Description: {query_data.get('description')}")
    
    payload = {
        "query": query_data["query"].strip(),
        "variables": query_data.get("variables", {})
    }
    
    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if "errors" in data and data["errors"]:
                print(f"❌ GraphQL Error:")
                error = data["errors"][0]
                print(f"   Message: {error.get('message')}")
                print(f"   Code: {error.get('extensions', {}).get('apiCode')}")
                
            elif "data" in data:
                result = data.get("data", {})
                # Count items returned
                for key in result.keys():
                    if isinstance(result[key], dict):
                        items = result[key].get("items", [])
                        meta = result[key].get("meta", {})
                        print(f"✅ SUCCESS!")
                        print(f"   Query: {key}")
                        print(f"   Items: {len(items)}")
                        if meta:
                            print(f"   Total count: {meta.get('count')}")
                        if items:
                            print(f"   First item keys: {list(items[0].keys())[:5]}...")
            else:
                print(f"⚠️ Unexpected response: {list(data.keys())}")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout (15s)")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("""
If you see ✅ SUCCESS for any query:
  → That query type has access
  
If all queries show ❌ Forbidden:
  → API key may not have read permissions
  → Contact SportsDynamics support

If specific queries work:
  → Use those for scraping
  → Adjust permissions as needed
""")
print("="*70 + "\n")
