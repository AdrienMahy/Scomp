#!/usr/bin/env python3
"""
Example: Using Predefined Filters
==================================

This shows how to use the predefined_filters.json to build
GraphQL payloads from simple values.
"""

import sys
from pathlib import Path
import json

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from src.config.filter_config import get_filter_config

print("\n" + "="*80)
print("PREDEFINED FILTERS - HOW TO USE")
print("="*80)

config = get_filter_config()

# ============================================================================
# EXAMPLE 1: See predefined filters for a query
# ============================================================================

print("\n1️⃣ VIEW PREDEFINED FILTERS FOR 'get_games':")
print("-" * 80)

predefined = config.get_predefined_filters("get_games")
for filter_name, filter_def in predefined.items():
    print(f"\n  📌 {filter_name}")
    print(f"     Label: {filter_def['label']}")
    print(f"     Type: {filter_def['type']}")
    print(f"     Required: {filter_def.get('required', False)}")
    print(f"     GraphQL Path: {filter_def['graphql_path']}")
    print(f"     Operator: {filter_def['operator']}")


# ============================================================================
# EXAMPLE 2: Build payload from simple values
# ============================================================================

print("\n" + "-" * 80)
print("2️⃣ BUILD PAYLOAD FROM SIMPLE VALUES:")
print("-" * 80)

# Define simple filter values
filter_values = {
    "available": True,
    "competition_id": "c6622467-55cb-4eda-bb77-f42ea74da9eb",
    "season_id": "2024"
}

print(f"\nInput values:")
print(json.dumps(filter_values, indent=2))

# Build GraphQL payload
payload = config.build_payload_from_values("get_games", filter_values)

print(f"\nBuilt GraphQL payload:")
print(json.dumps(payload, indent=2))

# This payload is ready to use in your GraphQL query!


# ============================================================================
# EXAMPLE 3: Validate required filters
# ============================================================================

print("\n" + "-" * 80)
print("3️⃣ VALIDATE REQUIRED FILTERS:")
print("-" * 80)

# Get required filters for a query
required = config.get_required_filters("get_seasons")
print(f"\nRequired filters for 'get_seasons': {required}")

# Validate that required filters are provided
values_valid = {
    "competition_id": "comp-123"
}

is_valid, missing = config.validate_required_filters("get_seasons", values_valid)
print(f"\nValidation result:")
print(f"  Valid: {is_valid}")
print(f"  Missing: {missing}")

# Try with invalid values
values_invalid = {"season_id": "2024"}  # Missing competition_id
is_valid, missing = config.validate_required_filters("get_seasons", values_invalid)
print(f"\nValidation result (missing competition_id):")
print(f"  Valid: {is_valid}")
print(f"  Missing: {missing}")


# ============================================================================
# EXAMPLE 4: Complete workflow
# ============================================================================

print("\n" + "-" * 80)
print("4️⃣ COMPLETE WORKFLOW:")
print("-" * 80)

def scrape_with_filters(query_name: str, filter_values: dict):
    """
    Complete example: from values to GraphQL query
    """
    print(f"\nScraping '{query_name}' with filters...")
    
    # Step 1: Validate required filters
    is_valid, missing = config.validate_required_filters(query_name, filter_values)
    if not is_valid:
        print(f"  ❌ Error: Missing required filters: {missing}")
        return None
    print(f"  ✅ All required filters provided")
    
    # Step 2: Build filter payload
    payload = config.build_payload_from_values(query_name, filter_values)
    print(f"  ✅ Filter payload built")
    print(f"     {json.dumps(payload, indent=6)}")
    
    # Step 3: Get pagination
    pagination = config.get_pagination_config(query_name)
    print(f"  ✅ Pagination: limit={pagination['limit']}, page={pagination['page']}")
    
    # Step 4: Would execute GraphQL query here
    print(f"  ✅ Ready to execute GraphQL query")
    
    return {
        "filters": payload,
        "pagination": pagination
    }

# Test it
result = scrape_with_filters("get_games", {
    "available": True,
    "competition_id": "comp-123",
    "season_id": "2024"
})


# ============================================================================
# EXAMPLE 5: Different value types
# ============================================================================

print("\n" + "-" * 80)
print("5️⃣ DIFFERENT FILTER VALUE TYPES:")
print("-" * 80)

# Example with different types
mixed_values = {
    "available": True,                    # boolean
    "competition_id": "comp-123",         # string
    "team_id": "team-456",                # string
    "result": "HOME_WIN",                 # enum/string
    "starts_at_from": "2024-01-01T00:00:00Z",  # datetime
}

print(f"\nMixed value types:")
print(json.dumps(mixed_values, indent=2))

payload = config.build_payload_from_values("get_games", mixed_values)

print(f"\nBuilt payload:")
print(json.dumps(payload, indent=2))


# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*80)
print("SUMMARY - HOW TO USE PREDEFINED FILTERS")
print("="*80)

print("""
1. VIEW AVAILABLE FILTERS:
   predefined = config.get_predefined_filters("get_games")

2. PREPARE SIMPLE VALUES:
   values = {
       "available": True,
       "competition_id": "comp-123",
       "season_id": "2024"
   }

3. BUILD GRAPHQL PAYLOAD:
   payload = config.build_payload_from_values("get_games", values)

4. VALIDATE REQUIRED FILTERS:
   is_valid, missing = config.validate_required_filters("get_games", values)
   if not is_valid:
       print(f"Missing: {missing}")

5. USE IN GRAPHQL QUERY:
   query = '''
   query GetGames($filters: GameFilters, $limit: Int) {
       games(filters: $filters, limit: $limit) {
           id name startsAt
       }
   }
   '''
   variables = {
       "filters": payload,
       "limit": 100
   }
   result = client.query(query, variables)
""")

print("="*80 + "\n")
