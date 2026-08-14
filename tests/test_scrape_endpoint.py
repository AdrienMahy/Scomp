#!/usr/bin/env python3
"""
Test script for POST /games/scrape endpoint

Run the FastAPI server first:
    cd backend
    python -m uvicorn src.main:app --reload

Then run this script:
    python tests/test_scrape_endpoint.py
"""

import requests
import json
from pathlib import Path
from typing import Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:8000"
GAMES_ENDPOINT = f"{API_BASE_URL}/games"

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
END = "\033[0m"


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{BLUE}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✅ {text}{END}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}❌ {text}{END}")


def print_info(text: str):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {text}{END}")


def test_get_filters():
    """Test GET /games/filters endpoint"""
    print_header("TEST 1: Get Available Filters")
    
    try:
        response = requests.get(f"{GAMES_ENDPOINT}/filters")
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Got {len(data.get('filters', {}))} available filters")
        
        print(f"\n{BLUE}Available Filters:{END}")
        filters = data.get("filters", {})
        for filter_name, filter_config in filters.items():
            print(f"  • {filter_name}: {filter_config.get('type')} ({filter_config.get('operator')})")
        
        return data.get("filters", {})
        
    except requests.RequestException as e:
        print_error(f"Failed to get filters: {e}")
        return None


def test_scrape_games_simple():
    """Test POST /games/scrape with minimal filters"""
    print_header("TEST 2: Scrape Games (Simple)")
    
    payload = {
        "competition_id": "comp-ligue1-2024",
        "limit": 5,
        "page": 1
    }
    
    print(f"Request payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(f"{GAMES_ENDPOINT}/scrape", json=payload)
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Scraped {data.get('count', 0)} games")
        
        if data.get('games'):
            print(f"\n{BLUE}First game:{END}")
            first_game = data['games'][0]
            print(json.dumps(first_game, indent=2))
        
        return data
        
    except requests.RequestException as e:
        print_error(f"Scrape failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        return None


def test_scrape_games_with_filters():
    """Test POST /games/scrape with multiple filters"""
    print_header("TEST 3: Scrape Games (With Filters)")
    
    payload = {
        "competition_id": "comp-ligue1-2024",
        "season_id": "season-2024-2025",
        "round_names": ["Round 1", "Round 2"],
        "limit": 10,
        "page": 1
    }
    
    print(f"Request payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(f"{GAMES_ENDPOINT}/scrape", json=payload)
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Scraped {data.get('count', 0)} games with filters")
        
        if data.get('games'):
            print(f"\n{BLUE}Games found:{END}")
            for game in data['games'][:3]:  # Show first 3
                print(f"  • {game.get('name')} ({game.get('round_name')})")
        
        return data
        
    except requests.RequestException as e:
        print_error(f"Filtered scrape failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        return None


def test_scrape_test_endpoint():
    """Test GET /games/scrape/test quick test endpoint"""
    print_header("TEST 4: Quick Test Endpoint")
    
    try:
        response = requests.get(f"{GAMES_ENDPOINT}/scrape/test")
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Test scrape returned {data.get('count', 0)} games")
        print_info(f"Message: {data.get('message', 'N/A')}")
        
        return data
        
    except requests.RequestException as e:
        print_error(f"Test endpoint failed: {e}")
        return None


def test_list_games_from_db():
    """Test GET /games to list games already in database"""
    print_header("TEST 5: List Games from Database")
    
    try:
        response = requests.get(f"{GAMES_ENDPOINT}", params={"limit": 5, "skip": 0})
        response.raise_for_status()
        
        data = response.json()
        print_success(f"Found {len(data)} games in database")
        
        if data:
            print(f"\n{BLUE}First game from DB:{END}")
            print(json.dumps(data[0], indent=2, default=str))
        
        return data
        
    except requests.RequestException as e:
        print_error(f"List games failed: {e}")
        return None


def test_health_check():
    """Test basic API health"""
    print_header("TEST 0: API Health Check")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        response.raise_for_status()
        
        data = response.json()
        print_success(f"API is healthy: {data.get('status')}")
        return True
        
    except requests.RequestException as e:
        print_error(f"Health check failed: {e}")
        print_error("Make sure the FastAPI server is running!")
        return False


def main():
    """Run all tests"""
    print(f"{YELLOW}{'='*70}")
    print("SCOMP GAMES SCRAPING ENDPOINT TEST SUITE")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"{'='*70}{END}\n")
    
    # Health check first
    if not test_health_check():
        print_error("\nCannot proceed - API is not accessible")
        print_info("Start the API with: cd backend && python -m uvicorn src.main:app --reload")
        return
    
    # Run tests
    filters = test_get_filters()
    
    test_scrape_games_simple()
    
    test_scrape_games_with_filters()
    
    test_scrape_test_endpoint()
    
    test_list_games_from_db()
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"{GREEN}All tests completed!{END}")
    print(f"\nNext steps:")
    print(f"  1. Check database for persisted games")
    print(f"  2. Verify filters are being applied correctly")
    print(f"  3. Test with different competition/season IDs")


if __name__ == "__main__":
    main()
