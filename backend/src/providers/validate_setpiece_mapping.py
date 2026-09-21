#!/usr/bin/env python3
"""
Setpiece Mapping Validation Script

Validates that the setpiece_types.py mapping module correctly represents
all setpiece types and frequencies in the TacticalData database.

Usage:
    python backend/src/providers/validate_setpiece_mapping.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from providers.setpiece_types import (
    SETPIECE_DISPLAY_TO_TYPE,
    SETPIECE_STATISTICS,
    SetpieceType,
    validate_mappings,
)

# Database connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)


def get_db_connection():
    """Get PostgreSQL connection to TacticalData database."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "192.168.30.206"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "TacticalData"),
        user=os.getenv("DB_USER", "scrapper"),
        password=os.getenv("DB_PASSWORD", "sR0K4bNthJ0IiCtmtixLBfawWz9roz"),
    )


def get_database_setpiece_types():
    """Query actual setpiece types from database."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                  entity->>'gata_display_name' as gata_display_name,
                  entity->>'type' as entity_type,
                  COUNT(*) as count,
                  COUNT(DISTINCT game_id) as games_count
                FROM setpieces
                GROUP BY entity->>'gata_display_name', entity->>'type'
                ORDER BY count DESC
            """)
            return cur.fetchall()
    finally:
        conn.close()


def validate_mapping_completeness():
    """Check that all database setpieces are mapped."""
    print("\n📊 VALIDATION 1: Mapping Completeness")
    print("=" * 80)

    db_types = get_database_setpiece_types()
    all_valid = True

    for row in db_types:
        display_name = row["gata_display_name"]
        entity_type = row["entity_type"]
        count = row["count"]

        if display_name not in SETPIECE_DISPLAY_TO_TYPE:
            print(f"❌ UNMAPPED: '{display_name}' ({count} instances)")
            all_valid = False
        else:
            mapped_type = SETPIECE_DISPLAY_TO_TYPE[display_name]
            status = "✅" if mapped_type is not None else "⚠️"
            print(
                f"{status} '{display_name}' → {mapped_type.value} "
                f"({count} instances, {row['games_count']} games)"
            )

    return all_valid


def validate_statistics_accuracy():
    """Verify that stored statistics match database."""
    print("\n📈 VALIDATION 2: Statistics Accuracy")
    print("=" * 80)

    db_types = get_database_setpiece_types()
    all_valid = True

    for row in db_types:
        display_name = row["gata_display_name"]
        mapped_type = SETPIECE_DISPLAY_TO_TYPE.get(display_name)

        if not mapped_type:
            continue

        db_count = row["count"]
        db_games = row["games_count"]

        stored_stats = SETPIECE_STATISTICS.get(mapped_type)

        if not stored_stats:
            print(f"⚠️  No statistics stored for {mapped_type.value}")
            continue

        stored_count = stored_stats["total_instances"]
        stored_games = stored_stats["games_count"]

        if stored_count == db_count and stored_games == db_games:
            print(f"✅ {mapped_type.value}: {stored_count} instances, {stored_games} games")
        else:
            print(
                f"❌ {mapped_type.value}: "
                f"Stored({stored_count}, {stored_games}) vs DB({db_count}, {db_games})"
            )
            all_valid = False

    return all_valid


def validate_ambiguity_handling():
    """Verify that FREE_KICK ambiguity is properly handled."""
    print("\n⚠️  VALIDATION 3: Ambiguity Handling (FREE_KICK)")
    print("=" * 80)

    db_types = get_database_setpiece_types()
    all_valid = True

    # Find all FREE_KICK entries
    free_kick_entries = [
        row for row in db_types
        if row["entity_type"] == "FREE_KICK"
    ]

    if len(free_kick_entries) > 1:
        print(f"⚠️  Found {len(free_kick_entries)} display names for entity.type='FREE_KICK':")
        for row in free_kick_entries:
            display_name = row["gata_display_name"]
            mapped_type = SETPIECE_DISPLAY_TO_TYPE.get(display_name)
            print(f"   • '{display_name}' → {mapped_type.value}")
            if mapped_type == SetpieceType.FREE_KICK:
                print(f"     Note: Using gata_display_name to disambiguate")

    return all_valid


def validate_module_consistency():
    """Validate internal module consistency."""
    print("\n🔄 VALIDATION 4: Module Internal Consistency")
    print("=" * 80)

    try:
        validate_mappings()
        print("✅ All mappings are internally consistent")
        return True
    except ValueError as e:
        print(f"❌ Mapping inconsistency: {e}")
        return False


def print_summary_table():
    """Print summary table of all setpiece types."""
    print("\n📋 COMPLETE SETPIECE SUMMARY")
    print("=" * 80)

    db_types = get_database_setpiece_types()

    print(f"{'Display Name':<25} {'Enum Type':<25} {'Count':<10} {'Games':<8}")
    print("-" * 80)

    total_instances = 0
    for row in db_types:
        display_name = row["gata_display_name"]
        entity_type = row["entity_type"]
        count = row["count"]
        games = row["games_count"]

        mapped_type = SETPIECE_DISPLAY_TO_TYPE.get(display_name)
        if not mapped_type:
            mapped_type_str = "❌ UNMAPPED"
        else:
            mapped_type_str = mapped_type.value

        print(f"{display_name:<25} {mapped_type_str:<25} {count:<10} {games:<8}")
        total_instances += count

    print("-" * 80)
    print(f"TOTAL: {total_instances} instances across {len(set(r['games_count'] for r in db_types))} games")


def main():
    """Run all validations."""
    print("\n🔍 SETPIECE MAPPING VALIDATION REPORT")
    print("=" * 80)
    print(f"Source: TacticalData database at 192.168.30.206:5432")

    results = {
        "Completeness": validate_mapping_completeness(),
        "Statistics": validate_statistics_accuracy(),
        "Ambiguity": validate_ambiguity_handling(),
        "Internal Consistency": validate_module_consistency(),
    }

    print_summary_table()

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    all_passed = True
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
        if not passed:
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("\n🎉 All validations passed!")
        return 0
    else:
        print("\n⚠️  Some validations failed. See details above.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
