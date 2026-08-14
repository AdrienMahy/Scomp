#!/usr/bin/env python3
"""Debug script to test endpoint in Docker"""
import sys
import os
import json
from pathlib import Path
import requests

# Set up path
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

print("="*60)
print("DIAGNOSTIC: Scraping Endpoint Test in Docker")
print("="*60)

# Test 1: Check file system
print("\n[1] File System Check:")
print(f"  CWD: {os.getcwd()}")
print(f"  /app/start/ID.json exists: {Path('/app/start/ID.json').exists()}")

# Test 2: Test the endpoint
print("\n[2] Testing /games/scrape Endpoint:")
try:
    response = requests.post(
        "http://localhost:8001/games/scrape",
        json={
            "league_name": "Ligue 2",
            "season_name": "2026 - 2027",
            "round": "1",
            "limit": 1
        },
        timeout=10
    )
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print("\n" + "="*60)

