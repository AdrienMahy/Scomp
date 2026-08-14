#!/usr/bin/env python3
"""
Debug: Print complete request details without masking
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

print("\n" + "="*80)
print("COMPLETE REQUEST DEBUG - NO MASKING")
print("="*80)

# Load query
with open(queries_file, 'r') as f:
    all_queries = json.load(f)

query_data = all_queries["get_competitions"]

# Build payload
payload = {
    "query": query_data["query"].strip(),
    "variables": query_data.get("variables", {})
}

# Build headers
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

# Print everything
print("\n🔗 URL:")
print("-" * 80)
print(api_url)

print("\n📝 HEADERS (Complete):")
print("-" * 80)
for key, value in headers.items():
    print(f"{key}: {value}")

print("\n📊 VARIABLES:")
print("-" * 80)
print(json.dumps(payload["variables"], indent=2))

print("\n🔍 QUERY:")
print("-" * 80)
print(payload["query"])

print("\n📦 FULL PAYLOAD:")
print("-" * 80)
print(json.dumps(payload, indent=2))

# Send request
print("\n\n" + "="*80)
print("SENDING REQUEST...")
print("="*80)

try:
    response = requests.post(
        api_url,
        json=payload,
        headers=headers,
        timeout=15
    )
    
    print(f"\n✅ Response Status: {response.status_code}")
    
    print("\n📥 RESPONSE HEADERS:")
    print("-" * 80)
    for key, value in response.headers.items():
        print(f"{key}: {value}")
    
    print("\n📄 RESPONSE BODY (Raw):")
    print("-" * 80)
    print(response.text)
    
    print("\n📄 RESPONSE BODY (Formatted):")
    print("-" * 80)
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print("(Could not parse as JSON)")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80 + "\n")
