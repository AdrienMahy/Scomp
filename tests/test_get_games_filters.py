#!/usr/bin/env python3
"""Test configured get_games filters"""
import sys
from pathlib import Path
import json

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from src.config.filter_config import get_filter_config

config = get_filter_config()

print("\n" + "="*80)
print("GET_GAMES - FILTRES CONFIGURÉS")
print("="*80)

predefined = config.get_predefined_filters("get_games")
print(f"\nFiltres disponibles: {list(predefined.keys())}\n")

for filter_name, filter_def in predefined.items():
    print(f"  📌 {filter_name}")
    print(f"     Label: {filter_def['label']}")
    print(f"     Type: {filter_def['type']}")
    print(f"     GraphQL Path: {filter_def['graphql_path']}")
    print(f"     Operator: {filter_def['operator']}\n")

# Test avec les 3 filtres
print("="*80)
print("EXEMPLE D'UTILISATION")
print("="*80)

values = {
    "available": True,
    "competition_id": "c6622467-55cb-4eda-bb77-f42ea74da9eb",
    "round": "Round 1"
}

print(f"\nValeurs fournies:")
print(json.dumps(values, indent=2))

payload = config.build_payload_from_values("get_games", values)

print(f"\nPayload GraphQL généré:")
print(json.dumps(payload, indent=2))

print("\n" + "="*80)
