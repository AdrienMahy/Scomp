"""
RGD JSON to Setpieces Table ETL Transformer

Transforms raw RGD setpiece entities into structured JSONB records
following the SETPIECES_SQL_STRUCTURE.json schema.

Key responsibilities:
1. Extract critical columns for BTREE indices (team_id, player_id, gata_display_name)
2. Build core JSONB sections (entity, time, spatial, actors, phase, channel)
3. Map RGD fields to correct type-specific section (only ONE per setpiece)
4. Handle type determination via gata_display_name (source of truth)
5. Validate and clean data before persistence
"""

import json
import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class SetpieceType(str, Enum):
    """Valid setpiece type values matching gata_display_name"""
    CORNER_KICK = "corner_kick"
    FREE_KICK = "free_kick"
    INDIRECT_FREE_KICK = "indirect_free_kick"
    THROW_IN = "throw_in"
    DIRECT_THROW_IN = "direct_throw_in"


# Mapping from gata_display_name (source of truth) to SetpieceType enum
# Supports multiple variations (with/without hyphens, case-insensitive)
GATA_DISPLAY_TO_TYPE = {
    "corner kick": SetpieceType.CORNER_KICK,
    "corner-kick": SetpieceType.CORNER_KICK,
    "Corner kick": SetpieceType.CORNER_KICK,
    "Corner-kick": SetpieceType.CORNER_KICK,
    
    "free kick": SetpieceType.FREE_KICK,
    "free-kick": SetpieceType.FREE_KICK,
    "direct free kick": SetpieceType.FREE_KICK,
    "direct free-kick": SetpieceType.FREE_KICK,
    "Free kick": SetpieceType.FREE_KICK,
    "Free-kick": SetpieceType.FREE_KICK,
    "Direct free kick": SetpieceType.FREE_KICK,
    "Direct free-kick": SetpieceType.FREE_KICK,
    
    "indirect free kick": SetpieceType.INDIRECT_FREE_KICK,
    "indirect free-kick": SetpieceType.INDIRECT_FREE_KICK,
    "Indirect free kick": SetpieceType.INDIRECT_FREE_KICK,
    "Indirect free-kick": SetpieceType.INDIRECT_FREE_KICK,
    
    "throw in": SetpieceType.THROW_IN,
    "throw-in": SetpieceType.THROW_IN,
    "Throw in": SetpieceType.THROW_IN,
    "Throw-in": SetpieceType.THROW_IN,
    
    "direct throw in": SetpieceType.DIRECT_THROW_IN,
    "direct throw-in": SetpieceType.DIRECT_THROW_IN,
    "direct-throw-in": SetpieceType.DIRECT_THROW_IN,
    "Direct Throw-in": SetpieceType.DIRECT_THROW_IN,
    "Direct throw-in": SetpieceType.DIRECT_THROW_IN,
}


@dataclass
class SetpieceRecord:
    """Represents a single setpiece row for the setpieces table"""
    
    # Metadata
    id: str
    game_id: str
    created_at: datetime
    updated_at: datetime
    
    # Critical extracted columns (BTREE indices)
    period_id: Optional[int] = None
    team_id: Optional[str] = None
    opponent_team_id: Optional[str] = None
    player_id: Optional[str] = None
    gata_display_name: Optional[str] = None
    
    # Core JSONB sections (always present)
    entity: Optional[Dict[str, Any]] = None
    time: Optional[Dict[str, Any]] = None
    spatial: Optional[Dict[str, Any]] = None
    actors: Optional[Dict[str, Any]] = None
    phase: Optional[Dict[str, Any]] = None
    channel: Optional[Dict[str, Any]] = None
    
    # Type-specific sections (only ONE is populated)
    corner_kick: Optional[Dict[str, Any]] = None
    free_kick: Optional[Dict[str, Any]] = None
    indirect_free_kick: Optional[Dict[str, Any]] = None
    throw_in: Optional[Dict[str, Any]] = None
    direct_throw_in: Optional[Dict[str, Any]] = None


class RGDToSetpiecesTransformer:
    """
    Transforms RGD JSON setpiece entities into Setpieces table records.
    
    Strategy:
    1. Determine type from gata_display_name (authoritative source)
    2. Extract critical columns for BTREE indices
    3. Build core JSONB sections applicable to all types
    4. Map RGD fields to type-specific JSONB section
    5. Validate referential integrity
    
    Field mapping reference: see RGD_TO_SETPIECES_MAPPING.json
    """
    
    # Critical column extraction: column_name → (section, path_in_section)
    CRITICAL_COLUMNS = {
        "period_id": ("time", "period_id"),
        "team_id": ("actors", "team"),
        "opponent_team_id": ("actors", "opponent_team"),
        "player_id": ("actors", "player"),
        "gata_display_name": ("entity", "gata_display_name"),
    }
    
    # Core JSONB sections present in ALL setpiece types
    CORE_SECTIONS = ["entity", "time", "spatial", "actors", "phase", "channel"]
    
    # Type-specific sections (mutually exclusive - only ONE per setpiece)
    TYPE_SPECIFIC_SECTIONS = {
        SetpieceType.CORNER_KICK: "corner_kick",
        SetpieceType.FREE_KICK: "free_kick",
        SetpieceType.INDIRECT_FREE_KICK: "indirect_free_kick",
        SetpieceType.THROW_IN: "throw_in",
        SetpieceType.DIRECT_THROW_IN: "direct_throw_in",
    }
    
    def __init__(self, game_id: str):
        """
        Initialize transformer for a specific game.
        
        Args:
            game_id: UUID of the game being processed
        """
        self.game_id = game_id
        self.timestamp = datetime.utcnow()
        self.stats = {
            "total_entities": 0,
            "by_type": {t.value: 0 for t in SetpieceType},
            "extracted_columns": {k: 0 for k in self.CRITICAL_COLUMNS.keys()},
            "errors": [],
        }
    
    def _get_nested_value(self, obj: Dict, path: str, default=None) -> Any:
        """
        Get nested value from dict using dot notation.
        
        Example: _get_nested_value(data, "actors.team") → data["actors"]["team"]
        """
        try:
            parts = path.split(".")
            value = obj
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return default
            return value
        except (KeyError, TypeError, AttributeError):
            return default
    
    def _set_nested_value(self, obj: Dict, path: str, value: Any) -> None:
        """
        Set nested value in dict using dot notation.
        
        Example: _set_nested_value(data, "actors.team", "team-123")
                 → data["actors"]["team"] = "team-123"
        """
        parts = path.split(".")
        current = obj
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def _determine_type(self, rgd_entity: Dict[str, Any]) -> Optional[SetpieceType]:
        """
        Determine setpiece type from gata_display_name (authoritative source).
        
        Checks both root level and nested 'entity.gata_display_name' for compatibility
        with raw RGD entities and pre-structured entities.
        
        Returns:
            SetpieceType if valid, None if not found
        """
        # Try root level first (raw RGD entities)
        gata_display = rgd_entity.get("gata_display_name")
        
        # Fall back to nested location (pre-structured entities)
        if not gata_display:
            gata_display = self._get_nested_value(rgd_entity, "entity.gata_display_name")
        
        if not gata_display:
            self.stats["errors"].append(f"Missing gata_display_name in entity")
            return None
        
        setpiece_type = GATA_DISPLAY_TO_TYPE.get(gata_display)
        if not setpiece_type:
            self.stats["errors"].append(f"Unknown gata_display_name: {gata_display}")
            return None
        
        return setpiece_type
    
    def _extract_critical_columns(self, rgd_entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract critical columns for BTREE indices.
        
        Checks root level first (for raw RGD entities), then nested paths.
        
        Returns dict with column_name → value mappings (only non-None values).
        """
        extracted = {}
        
        for col_name, (section, path_key) in self.CRITICAL_COLUMNS.items():
            # Try root level first (raw RGD entities)
            if col_name == "player_id":
                value = rgd_entity.get("player") or rgd_entity.get("taker")
            elif col_name == "team_id":
                value = rgd_entity.get("team")
            elif col_name == "opponent_team_id":
                value = rgd_entity.get("opponent_team")
            else:
                value = rgd_entity.get(col_name)
            
            # Fall back to nested location (pre-structured entities)
            if not value:
                full_path = f"{section}.{path_key}" if path_key else section
                value = self._get_nested_value(rgd_entity, full_path)
            
            if value is not None:
                extracted[col_name] = value
                self.stats["extracted_columns"][col_name] += 1
        
        return extracted
    
    def _build_core_jsonb_sections(
        self,
        rgd_entity: Dict[str, Any],
        extracted: Dict[str, Any],
        setpiece_type: SetpieceType
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build core JSONB sections (entity, time, spatial, actors, phase, channel).
        
        These sections are present in ALL setpiece types.
        """
        jsonb_sections = {}

        # SportsDynamics emits RGD setpieces as flat entities. Build the
        # normalized sections expected by the setpieces table from those keys.
        flat_section_keys = {
            "entity": ("entity_id", "sequence_id", "gata_display_name"),
            "time": (
                "period_id", "start", "end", "duration", "start_frame",
                "end_frame", "quick_restart", "time_to_restart",
            ),
            "spatial": (
                "side", "start_x", "start_y", "end_x", "end_y",
                "start_channel", "end_channel", "start_third", "end_third",
                "functional_start_zone", "functional_end_zone", "distance",
                "distance_gained",
            ),
            "actors": (
                "team", "opponent_team", "player", "taker", "goalkeeper",
                "targeted_player", "first_contact_player",
            ),
            "phase": (
                "possession", "individual_possession", "next_individual_possession",
                "phase_of_play", "phase_of_play_label", "play", "play_label",
            ),
            "channel": ("start_channel", "end_channel"),
        }
        
        for section in self.CORE_SECTIONS:
            if section in rgd_entity:
                section_data = json.loads(json.dumps(rgd_entity[section]))
            else:
                section_data = {
                    key: rgd_entity[key]
                    for key in flat_section_keys.get(section, ())
                    if key in rgd_entity and rgd_entity[key] is not None
                }
            
            if section == "entity" and isinstance(section_data, dict):
                # Keep entity for reference but it's already captured in critical columns
                pass
            
            elif section == "time" and isinstance(section_data, dict):
                # Keep time section as-is (period_id already extracted)
                pass
            
            if section_data:
                jsonb_sections[section] = section_data
        
        return jsonb_sections
    
    def _build_type_specific_section(
        self,
        rgd_entity: Dict[str, Any],
        setpiece_type: SetpieceType
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build type-specific JSONB section.
        
        Populates the matching type-specific section with ALL remaining fields
        from the RGD entity that aren't in core sections (entity, time, spatial, etc.).
        
        Returns dict with ONE key: setpiece_type.value → section_data
        All other type sections are None.
        
        Example: {"throw_in": {all_remaining_fields}, "corner_kick": None, ...}
        """
        type_specific = {}
        section_name = self.TYPE_SPECIFIC_SECTIONS[setpiece_type]
        
        # Collect ALL fields not already in core sections
        reserved_keys = set(self.CORE_SECTIONS) | {
            "id", "gata_display_name", "period_id", "team_id", 
            "opponent_team_id", "player_id"
        }
        
        section_data = {}
        for key, value in rgd_entity.items():
            if key not in reserved_keys:
                section_data[key] = value
        
        type_specific[section_name] = section_data if section_data else {}
        
        # All other type sections are None
        for type_enum, section_key in self.TYPE_SPECIFIC_SECTIONS.items():
            if type_enum != setpiece_type:
                type_specific[section_key] = None
        
        return type_specific
    
    def transform_entity(self, rgd_entity: Dict[str, Any]) -> Optional[SetpieceRecord]:
        """
        Transform a single RGD entity into a SetpieceRecord.
        
        Args:
            rgd_entity: Dictionary from RGD JSON entities array
            
        Returns:
            SetpieceRecord ready for database insertion, or None if validation fails
        """
        self.stats["total_entities"] += 1
        
        # Step 1: Determine type from gata_display_name
        setpiece_type = self._determine_type(rgd_entity)
        if not setpiece_type:
            return None
        
        self.stats["by_type"][setpiece_type.value] += 1
        
        # Step 2: Extract critical columns
        extracted = self._extract_critical_columns(rgd_entity)
        
        # Step 3: Build core JSONB sections
        core_sections = self._build_core_jsonb_sections(rgd_entity, extracted, setpiece_type)
        
        # Step 4: Build type-specific section
        type_sections = self._build_type_specific_section(rgd_entity, setpiece_type)
        
        # Step 5: Create SetpieceRecord
        record = SetpieceRecord(
            id=str(uuid.uuid4()),
            game_id=self.game_id,
            created_at=self.timestamp,
            updated_at=self.timestamp,
            # Critical columns
            period_id=extracted.get("period_id"),
            team_id=extracted.get("team_id"),
            opponent_team_id=extracted.get("opponent_team_id"),
            player_id=extracted.get("player_id"),
            gata_display_name=extracted.get("gata_display_name"),
            # Core sections
            entity=core_sections.get("entity"),
            time=core_sections.get("time"),
            spatial=core_sections.get("spatial"),
            actors=core_sections.get("actors"),
            phase=core_sections.get("phase"),
            channel=core_sections.get("channel"),
            # Type-specific sections
            corner_kick=type_sections.get("corner_kick"),
            free_kick=type_sections.get("free_kick"),
            indirect_free_kick=type_sections.get("indirect_free_kick"),
            throw_in=type_sections.get("throw_in"),
            direct_throw_in=type_sections.get("direct_throw_in"),
        )
        
        return record
    
    def transform_batch(self, rgd_entities: list) -> Tuple[list, Dict[str, Any]]:
        """
        Transform a batch of RGD entities.
        
        Args:
            rgd_entities: List of RGD entity dictionaries
            
        Returns:
            Tuple of (records, stats)
            records: List of SetpieceRecord objects
            stats: Dictionary with transformation statistics
        """
        records = []
        
        for rgd_entity in rgd_entities:
            record = self.transform_entity(rgd_entity)
            if record:
                records.append(record)
        
        return records, self.stats
    
    def records_to_dicts(self, records: list) -> list:
        """Convert SetpieceRecord dataclasses to dictionaries for ORM insertion"""
        return [asdict(r) for r in records]
