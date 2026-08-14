#!/usr/bin/env python3
"""
Test script demonstrating filter config usage
"""
import sys
from pathlib import Path
import json

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from src.config.filter_config import get_filter_config

print("\n" + "="*80)
print("GRAPHQL FILTER CONFIGURATION DEMO")
print("="*80)

# Load config
config = get_filter_config()

# 1. List all queries
print("\n1️⃣ AVAILABLE QUERIES:")
print("-" * 80)
queries = config.list_all_queries()
for q in queries:
    q_config = config.get_query_config(q)
    print(f"  • {q}")
    print(f"    Name: {q_config.get('name')}")
    print(f"    Description: {q_config.get('description')}")

# 2. Show available filters for get_games
print("\n2️⃣ AVAILABLE FILTERS FOR 'get_games':")
print("-" * 80)
filters = config.get_available_filters("get_games")
for f in filters:
    print(f"  • {f}")

# 3. Show example filters
print("\n3️⃣ EXAMPLE FILTERS FOR 'get_games':")
print("-" * 80)
example = config.get_example_filters("get_games")
print(json.dumps(example, indent=2))

# 4. Validate filters
print("\n4️⃣ VALIDATE FILTERS FOR 'get_games':")
print("-" * 80)
test_filters = [
    "competition.id",
    "season.id",
    "round.name",
    "invalid_filter"
]
for f in test_filters:
    is_valid = config.validate_filter("get_games", f)
    status = "✅ Valid" if is_valid else "❌ Invalid"
    print(f"  {status}: {f}")

# 5. Show pagination config
print("\n5️⃣ PAGINATION CONFIG FOR 'get_games':")
print("-" * 80)
pagination = config.get_pagination_config("get_games")
print(json.dumps(pagination, indent=2))

# 6. Show filter operators
print("\n6️⃣ AVAILABLE FILTER OPERATORS:")
print("-" * 80)
operators = config.get_filter_operators()
print(json.dumps(operators, indent=2))

# 7. Build filter payload example
print("\n7️⃣ BUILD FILTER PAYLOAD EXAMPLE:")
print("-" * 80)
custom_filters = {
    "competition": {
        "id": {
            "equals": "c6622467-55cb-4eda-bb77-f42ea74da9eb"
        }
    },
    "round": {
        "name": {
            "in": ["Matchday 1", "Matchday 2"]
        }
    }
}
payload = config.build_filter_payload("get_games", custom_filters)
print("Built payload:")
print(json.dumps(payload, indent=2))

print("\n" + "="*80)
print("✅ Filter config is ready to use in your application!")
print("="*80 + "\n")
