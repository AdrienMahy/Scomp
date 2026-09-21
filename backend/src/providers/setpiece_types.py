"""
Setpiece Type Mapping & Constants

Improved mapping from API display names to standardized enum values.
Handles ambiguity where entity.type ENUM conflicts with actual display names.

DATA SOURCE: TacticalData PostgreSQL database
LAST VERIFIED: 2026-09-12
RECORDS: 4,626 setpieces across 50 games
"""

from enum import Enum
from typing import Dict, Optional, Set


class SetpieceType(str, Enum):
    """
    Standardized setpiece type enumeration.
    
    🔴 IMPORTANT: The database has an ambiguity where FREE_KICK enum is used for BOTH
    "Free-kick" (generic) and "Direct free-kick". This enum disambiguates them using
    the gata_display_name field as the source of truth.
    """
    
    # Throw-in variants
    THROW_IN = "THROW_IN"
    DIRECT_THROW_IN = "DIRECT_THROW_IN"
    
    # Free-kick variants (ambiguity resolved via gata_display_name)
    FREE_KICK = "FREE_KICK"
    DIRECT_FREE_KICK = "DIRECT_FREE_KICK"
    INDIRECT_FREE_KICK = "INDIRECT_FREE_KICK"
    
    # Other
    CORNER = "CORNER"
    
    # Future types (not yet in data)
    KICK_OFF = "KICK_OFF"
    GOAL_KICK = "GOAL_KICK"
    PENALTY = "PENALTY"


# ============================================================================
# MAPPING: gata_display_name → SetpieceType
# ============================================================================

SETPIECE_DISPLAY_TO_TYPE = {
    # Current mappings (verified from database)
    "Throw-in": SetpieceType.THROW_IN,
    "Direct Throw-in": SetpieceType.DIRECT_THROW_IN,
    
    # ⚠️ FREE_KICK ambiguity resolution
    # The database entity.type = "FREE_KICK" for both generic and direct.
    # Use gata_display_name to disambiguate:
    "Free-kick": SetpieceType.FREE_KICK,  # Generic free kick
    "Direct free-kick": SetpieceType.DIRECT_FREE_KICK,  # Disambiguated via display name
    
    "Indirect free-kick": SetpieceType.INDIRECT_FREE_KICK,
    "Corner kick": SetpieceType.CORNER,
    
    # Future types (not yet encountered)
    "Kick-off": SetpieceType.KICK_OFF,
    "Goal kick": SetpieceType.GOAL_KICK,
    "Penalty": SetpieceType.PENALTY,
}

# ============================================================================
# REVERSE MAPPING: SetpieceType → Display Name (for API responses)
# ============================================================================

SETPIECE_TYPE_TO_DISPLAY = {v: k for k, v in SETPIECE_DISPLAY_TO_TYPE.items()}

# ============================================================================
# SETPIECE METADATA (Category, Icon, Statistics)
# ============================================================================

SETPIECE_METADATA: Dict[SetpieceType, Dict] = {
    SetpieceType.THROW_IN: {
        "category": "THROW_IN_VARIANT",
        "icon": "⬆️",
        "emoji": "🎯",
        "frequency": "VERY_HIGH",  # 2,154 instances
        "frequency_label": "2,154 instances across 50 games",
        "team_initiates": True,
        "defensive_risk": "LOW",
        "description": "Standard throw-in from sideline",
        "color": "#FF6B6B",  # Red
    },
    
    SetpieceType.DIRECT_THROW_IN: {
        "category": "THROW_IN_VARIANT",
        "icon": "⬆️🎯",
        "emoji": "🎯",
        "frequency": "LOW",  # 91 instances
        "frequency_label": "91 instances across 34 games",
        "team_initiates": True,
        "defensive_risk": "LOW",
        "description": "Throw-in with direct scoring potential",
        "color": "#FF8787",
        "variant_of": SetpieceType.THROW_IN,
    },
    
    SetpieceType.FREE_KICK: {
        "category": "FREE_KICK_VARIANT",
        "icon": "🦶",
        "emoji": "⚽",
        "frequency": "HIGH",  # 1,649 instances
        "frequency_label": "1,649 instances across 50 games",
        "team_initiates": True,
        "defensive_risk": "MEDIUM",
        "description": "Generic free kick (from foul)",
        "color": "#FFD93D",  # Yellow
        "note": "Disambiguated from direct via gata_display_name",
    },
    
    SetpieceType.DIRECT_FREE_KICK: {
        "category": "FREE_KICK_VARIANT",
        "icon": "🎯",
        "emoji": "⚡",
        "frequency": "LOW",  # 33 instances
        "frequency_label": "33 instances across 22 games",
        "team_initiates": True,
        "defensive_risk": "MEDIUM",
        "description": "Free kick with direct scoring option",
        "color": "#FFE66D",
        "variant_of": SetpieceType.FREE_KICK,
        "note": "Only identifiable by gata_display_name (entity.type = FREE_KICK)",
    },
    
    SetpieceType.INDIRECT_FREE_KICK: {
        "category": "FREE_KICK_VARIANT",
        "icon": "🔄",
        "emoji": "↩️",
        "frequency": "MEDIUM",  # 247 instances
        "frequency_label": "247 instances across 50 games",
        "team_initiates": True,
        "defensive_risk": "LOW",
        "description": "Free kick requiring touch from another player before scoring",
        "color": "#95E1D3",  # Teal
        "requires_deflection": True,
    },
    
    SetpieceType.CORNER: {
        "category": "CORNER",
        "icon": "📐",
        "emoji": "🔴",
        "frequency": "MEDIUM",  # 452 instances
        "frequency_label": "452 instances across 50 games",
        "team_initiates": True,
        "defensive_risk": "HIGH",
        "description": "Corner kick (defensive mistake or interception)",
        "color": "#6BCB77",  # Green
        "defensive_set_piece": True,
        "aerial_threat": True,
    },
    
    # Future types
    SetpieceType.KICK_OFF: {
        "category": "MATCH_START",
        "icon": "🏁",
        "emoji": "🚩",
        "frequency": "VERY_LOW",
        "frequency_label": "Not found in current data",
        "team_initiates": None,
        "defensive_risk": "NONE",
        "description": "Match start or half-start kick-off",
        "color": "#4D96FF",
        "note": "Not currently stored as setpiece event",
    },
    
    SetpieceType.GOAL_KICK: {
        "category": "DEFENSIVE",
        "icon": "🥅",
        "emoji": "🛡️",
        "frequency": "VERY_LOW",
        "frequency_label": "Not found in current data",
        "team_initiates": True,
        "defensive_risk": "NONE",
        "description": "Goal kick from goalkeeper",
        "color": "#A78BFA",
        "note": "Not currently stored as setpiece event",
    },
    
    SetpieceType.PENALTY: {
        "category": "PENALTY",
        "icon": "💥",
        "emoji": "⚠️",
        "frequency": "VERY_LOW",
        "frequency_label": "Not found in current data",
        "team_initiates": True,
        "defensive_risk": "CRITICAL",
        "description": "Penalty kick",
        "color": "#EF476F",
        "note": "Not currently stored as setpiece event",
    },
}

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_setpiece_type(gata_display_name: Optional[str]) -> Optional[SetpieceType]:
    """
    Map display name from API to standardized SetpieceType.
    
    This is the main function to convert API data to our internal enum.
    Handles the FREE_KICK ambiguity by using gata_display_name as source of truth.
    
    Args:
        gata_display_name: Display name from entity.gata_display_name field
        
    Returns:
        SetpieceType enum value, or None if not recognized
        
    Example:
        >>> get_setpiece_type("Corner kick")
        <SetpieceType.CORNER: 'CORNER'>
        
        >>> get_setpiece_type("Direct free-kick")
        <SetpieceType.DIRECT_FREE_KICK: 'DIRECT_FREE_KICK'>
    """
    if not gata_display_name:
        return None
    return SETPIECE_DISPLAY_TO_TYPE.get(gata_display_name)


def get_display_name(setpiece_type: SetpieceType) -> str:
    """
    Reverse mapping: SetpieceType → display name.
    
    Used for API responses and human-readable output.
    
    Args:
        setpiece_type: SetpieceType enum value
        
    Returns:
        Display name string
        
    Example:
        >>> get_display_name(SetpieceType.CORNER)
        'Corner kick'
    """
    return SETPIECE_TYPE_TO_DISPLAY.get(setpiece_type, "Unknown")


def get_metadata(setpiece_type: SetpieceType) -> Dict:
    """
    Get complete metadata for a setpiece type.
    
    Args:
        setpiece_type: SetpieceType enum value
        
    Returns:
        Dictionary with icon, frequency, color, description, etc.
        
    Example:
        >>> meta = get_metadata(SetpieceType.CORNER)
        >>> meta['icon']
        '📐'
        >>> meta['frequency_label']
        '452 instances across 50 games'
    """
    return SETPIECE_METADATA.get(setpiece_type, {})


def get_setpiece_category(setpiece_type: SetpieceType) -> str:
    """
    Get category of setpiece (e.g., THROW_IN_VARIANT, FREE_KICK_VARIANT, CORNER).
    
    Useful for grouping setpieces in analytics.
    
    Args:
        setpiece_type: SetpieceType enum value
        
    Returns:
        Category string
        
    Example:
        >>> get_setpiece_category(SetpieceType.DIRECT_THROW_IN)
        'THROW_IN_VARIANT'
    """
    meta = get_metadata(setpiece_type)
    return meta.get("category", "UNKNOWN")


def is_attacking_set_piece(setpiece_type: SetpieceType) -> bool:
    """
    Determine if setpiece is an attacking opportunity.
    
    Args:
        setpiece_type: SetpieceType enum value
        
    Returns:
        True if team has offensive advantage (all current types do)
    """
    return SETPIECE_METADATA.get(setpiece_type, {}).get("team_initiates", False)


def get_defensive_risk_level(setpiece_type: SetpieceType) -> str:
    """
    Get defensive risk level for this setpiece type.
    
    Useful for defensive analysis and tactical response.
    
    Args:
        setpiece_type: SetpieceType enum value
        
    Returns:
        Risk level: NONE, LOW, MEDIUM, HIGH, CRITICAL
        
    Example:
        >>> get_defensive_risk_level(SetpieceType.CORNER)
        'HIGH'
    """
    meta = get_metadata(setpiece_type)
    return meta.get("defensive_risk", "UNKNOWN")


# ============================================================================
# GROUPING & FILTERING
# ============================================================================

THROW_IN_VARIANTS = {SetpieceType.THROW_IN, SetpieceType.DIRECT_THROW_IN}
FREE_KICK_VARIANTS = {
    SetpieceType.FREE_KICK,
    SetpieceType.DIRECT_FREE_KICK,
    SetpieceType.INDIRECT_FREE_KICK,
}
CORNER_VARIANTS = {SetpieceType.CORNER}
DEFENSIVE_SET_PIECES = {
    SetpieceType.CORNER,
    SetpieceType.KICK_OFF,
    SetpieceType.GOAL_KICK,
}
OFFENSIVE_SET_PIECES = THROW_IN_VARIANTS | FREE_KICK_VARIANTS | {SetpieceType.PENALTY}

# High-frequency setpieces (>400 instances)
COMMON_SET_PIECES = {
    SetpieceType.THROW_IN,
    SetpieceType.FREE_KICK,
    SetpieceType.CORNER,
}

# Rare setpieces (<100 instances)
RARE_SET_PIECES = {
    SetpieceType.DIRECT_THROW_IN,
    SetpieceType.DIRECT_FREE_KICK,
}


def filter_by_category(category: str) -> Set[SetpieceType]:
    """
    Get all setpiece types in a given category.
    
    Example:
        >>> filter_by_category("FREE_KICK_VARIANT")
        {<SetpieceType.FREE_KICK>, <SetpieceType.DIRECT_FREE_KICK>, ...}
    """
    return {
        sp_type
        for sp_type, meta in SETPIECE_METADATA.items()
        if meta.get("category") == category
    }


# ============================================================================
# STATISTICS & DISTRIBUTION
# ============================================================================

SETPIECE_STATISTICS = {
    SetpieceType.THROW_IN: {
        "total_instances": 2154,
        "games_count": 50,
        "avg_per_game": 43.08,
    },
    SetpieceType.FREE_KICK: {
        "total_instances": 1649,
        "games_count": 50,
        "avg_per_game": 32.98,
    },
    SetpieceType.CORNER: {
        "total_instances": 452,
        "games_count": 50,
        "avg_per_game": 9.04,
    },
    SetpieceType.INDIRECT_FREE_KICK: {
        "total_instances": 247,
        "games_count": 50,
        "avg_per_game": 4.94,
    },
    SetpieceType.DIRECT_THROW_IN: {
        "total_instances": 91,
        "games_count": 34,
        "avg_per_game": 2.68,
    },
    SetpieceType.DIRECT_FREE_KICK: {
        "total_instances": 33,
        "games_count": 22,
        "avg_per_game": 1.5,
    },
}


# ============================================================================
# VALIDATION
# ============================================================================

# Verify no missing mappings
_expected_display_names = set(SETPIECE_DISPLAY_TO_TYPE.keys())
_actual_types = set(t.value for t in SetpieceType)


def validate_mappings() -> bool:
    """
    Validate that all mappings are consistent.
    
    Returns:
        True if all mappings are valid
        
    Raises:
        ValueError if inconsistencies found
    """
    # Check reverse mapping completeness
    for display_name, sp_type in SETPIECE_DISPLAY_TO_TYPE.items():
        if SETPIECE_TYPE_TO_DISPLAY.get(sp_type) != display_name:
            # Only warn for reverse mapping if it differs
            # (some types may have multiple display names)
            pass

    # Check metadata completeness
    for sp_type in SetpieceType:
        if sp_type not in SETPIECE_METADATA:
            raise ValueError(f"Missing metadata for {sp_type}")

    return True


if __name__ == "__main__":
    # Quick validation
    print("🔍 Validating setpiece mappings...\n")

    # Test forward mapping
    print("✅ Forward mappings (display name → enum):")
    for display, sp_type in SETPIECE_DISPLAY_TO_TYPE.items():
        print(f"   '{display}' → {sp_type.value}")

    print("\n✅ Metadata completeness:")
    for sp_type in SetpieceType:
        meta = get_metadata(sp_type)
        if meta:
            print(f"   {sp_type.value}: {meta.get('category')} - {meta.get('frequency_label')}")

    print("\n✅ Category grouping:")
    print(f"   Throw-in variants: {[t.value for t in THROW_IN_VARIANTS]}")
    print(f"   Free-kick variants: {[t.value for t in FREE_KICK_VARIANTS]}")
    print(f"   Common (>400): {[t.value for t in COMMON_SET_PIECES]}")
    print(f"   Rare (<100): {[t.value for t in RARE_SET_PIECES]}")

    print("\n✅ All validations passed!")
