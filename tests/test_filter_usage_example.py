#!/usr/bin/env python3
"""
Practical example: Using filters in actual scraping
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from src.config.filter_config import get_filter_config
from src.api.sportsdynamics import SportsDynamicsClient

# ============================================================================
# EXAMPLE 1: Simple - Use with default filters
# ============================================================================

print("\n" + "="*80)
print("EXAMPLE 1: Load filters and show pagination settings")
print("="*80)

config = get_filter_config()

# Get pagination for games
pagination = config.get_pagination_config("get_games")
print(f"Pagination for get_games:")
print(f"  Limit: {pagination['limit']}")
print(f"  Page: {pagination['page']}")


# ============================================================================
# EXAMPLE 2: Build a filter payload for API call
# ============================================================================

print("\n" + "="*80)
print("EXAMPLE 2: Build filter payload for GraphQL query")
print("="*80)

# Your custom filters (you'll fill these based on API discovery)
my_filters = {
    "available": {
        "equals": True
    }
}

# Build complete payload (merges with example_filters if any)
payload = config.build_filter_payload("get_games", my_filters)
print(f"Filter payload to send to API:")
print(f"  {payload}")


# ============================================================================
# EXAMPLE 3: Validate filters before using them
# ============================================================================

print("\n" + "="*80)
print("EXAMPLE 3: Validate filters before building query")
print("="*80)

filters_to_test = [
    "available",
    "competition.id",
    "season.id",
    "invalid_filter_name"
]

print("Checking which filters are available...")
for filter_name in filters_to_test:
    is_valid = config.validate_filter("get_games", filter_name)
    status = "✅ Available" if is_valid else "❌ Not available"
    print(f"  {filter_name}: {status}")


# ============================================================================
# EXAMPLE 4: Template - How to structure your API calls
# ============================================================================

print("\n" + "="*80)
print("EXAMPLE 4: Template for using filters in scraper")
print("="*80)

# This is how you would use it in your scraper
class GameScraper:
    def __init__(self):
        self.client = SportsDynamicsClient()
        self.config = get_filter_config()
    
    def scrape_with_filters(self, filters_dict: dict):
        """
        Scrape games with custom filters
        
        Args:
            filters_dict: Dict of filters to apply
                Example: {
                    "available": {"equals": True},
                    "competition": {"id": {"equals": "comp-id-123"}}
                }
        """
        # 1. Validate filters
        print("Step 1: Validating filters...")
        available_filters = self.config.get_available_filters("get_games")
        
        # 2. Build filter payload
        print("Step 2: Building filter payload...")
        filter_payload = self.config.build_filter_payload("get_games", filters_dict)
        
        # 3. Get pagination settings
        print("Step 3: Getting pagination settings...")
        pagination = self.config.get_pagination_config("get_games")
        
        # 4. Build GraphQL query (simplified)
        print("Step 4: Building GraphQL query...")
        query = f"""
        query GetGames {{
            games(filters: {filter_payload}) {{
                id
                name
                result
                startsAt
                playedAt
            }}
        }}
        """
        
        # 5. Execute query
        print("Step 5: Would execute query here...")
        print(f"  Filters: {filter_payload}")
        print(f"  Pagination: limit={pagination['limit']}, page={pagination['page']}")
        
        return {"games": []}

# Run example
scraper = GameScraper()
scraper.scrape_with_filters({
    "available": {"equals": True}
})


# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*80)
print("HOW TO USE IN YOUR ACTUAL SCRAPER")
print("="*80)

print("""
1. IMPORT the filter config:
   from src.config.filter_config import get_filter_config
   config = get_filter_config()

2. BUILD FILTER PAYLOAD:
   my_filters = {"available": {"equals": True}}
   payload = config.build_filter_payload("get_games", my_filters)

3. GET PAGINATION:
   pagination = config.get_pagination_config("get_games")

4. BUILD GRAPHQL QUERY:
   Use the payload and pagination in your GraphQL query

5. EXECUTE:
   response = client.query(query, variables)

6. UPDATE graphql_filters.json:
   Add filters that work to "available_filters" and "example_filters"
""")

print("="*80)
