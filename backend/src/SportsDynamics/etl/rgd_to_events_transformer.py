"""
RGD JSON to Events Table ETL Transformer

Extracts critical columns from RGD JSON events and prepares them for SQL insertion.
Implements hybrid schema: critical columns extracted + JSONB for flexible data.

Critical columns extracted (per event):
- period_id (time.period_id) → INTEGER
- player_id (actors.player) → UUID
- team_id (actors.team) → UUID
- opponent_team_id (actors.opponent_team) → UUID
- targeted_player_id (actors.targeted_player) → UUID
- goalkeeper_id (actors.goalkeeper) → UUID
- expected_defender_at_arrival_id (actors.expected_defender_at_arrival) → UUID
- previous_passer_id (actors.previous_passer) → UUID
- possession_id (phase.possession) → UUID
- type_of_play_id (phase.type_of_play) → UUID
- phase_of_play_id (phase.phase_of_play) → UUID
- individual_possession_id (phase.individual_possession) → UUID

Remaining data → JSONB columns (entity, time, phase, spatial, actors, etc.)
"""

import json
import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class EventRecord:
    """Represents a single event row for the events table"""
    # Metadata
    id: str
    game_id: str
    created_at: datetime
    updated_at: datetime
    
    # Critical extracted columns (BTREE indices)
    period_id: Optional[int] = None
    player_id: Optional[str] = None
    team_id: Optional[str] = None
    opponent_team_id: Optional[str] = None
    targeted_player_id: Optional[str] = None
    goalkeeper_id: Optional[str] = None
    expected_defender_at_arrival_id: Optional[str] = None
    previous_passer_id: Optional[str] = None
    
    # Phase critical columns (PRIMARY JOINTURE)
    possession_id: Optional[str] = None
    type_of_play_id: Optional[str] = None
    phase_of_play_id: Optional[str] = None
    individual_possession_id: Optional[str] = None
    
    # JSONB sections (GIN indices for nested queries)
    entity: Optional[Dict[str, Any]] = None
    time: Optional[Dict[str, Any]] = None
    phase: Optional[Dict[str, Any]] = None
    spatial: Optional[Dict[str, Any]] = None
    actors: Optional[Dict[str, Any]] = None
    receiver: Optional[Dict[str, Any]] = None
    channel: Optional[Dict[str, Any]] = None
    adds: Optional[Dict[str, Any]] = None
    pass_data: Optional[Dict[str, Any]] = None
    custom: Optional[Dict[str, Any]] = None
    cross: Optional[Dict[str, Any]] = None
    shot: Optional[Dict[str, Any]] = None
    boxentry: Optional[Dict[str, Any]] = None
    finalthirdentry: Optional[Dict[str, Any]] = None
    clearance: Optional[Dict[str, Any]] = None
    pressure: Optional[Dict[str, Any]] = None
    receivingrun: Optional[Dict[str, Any]] = None


class RGDToEventsTransformer:
    """
    Transforms RGD JSON entities into Events table records.
    
    Strategy:
    1. Extract critical UUID/INT columns for BTREE indices (fast jointures)
    2. Preserve remaining data in JSONB sections (flexibility)
    3. Maintain referential integrity with ForeignKey constraints
    """
    
    # Critical column extraction mapping: column_name → (section, path)
    CRITICAL_COLUMNS = {
        "period_id": ("time", "period_id"),
        "player_id": ("actors", "player"),
        "team_id": ("actors", "team"),
        "opponent_team_id": ("actors", "opponent_team"),
        "targeted_player_id": ("actors", "targeted_player"),
        "goalkeeper_id": ("actors", "goalkeeper"),
        "expected_defender_at_arrival_id": ("actors", "expected_defender_at_arrival"),
        "previous_passer_id": ("actors", "previous_passer"),
        # Phase jointure columns
        "possession_id": ("phase", "possession"),
        "type_of_play_id": ("phase", "type_of_play"),
        "phase_of_play_id": ("phase", "phase_of_play"),
        "individual_possession_id": ("phase", "individual_possession"),
    }
    
    # JSONB sections to preserve (these contain flexible/rarely-queried data)
    JSONB_SECTIONS = [
        "entity", "time", "phase", "spatial", "actors", "receiver",
        "channel", "adds", "pass", "custom", "cross", "shot",
        "boxentry", "finalthirdentry", "clearance", "pressure", "receivingrun"
    ]
    
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
            "extracted_columns": {k: 0 for k in self.CRITICAL_COLUMNS.keys()},
            "errors": [],
        }
    
    def _get_nested_value(self, obj: Dict, path: str, default=None) -> Any:
        """
        Get nested value from dict using dot notation path.
        
        Example: _get_nested_value(data, "actors.player") → data["actors"]["player"]
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
    
    def _extract_critical_columns(self, rgd_entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract critical columns from RGD entity.
        
        Returns dict with column_name → value mappings.
        Only includes non-None values.
        """
        extracted = {}
        
        for col_name, (section, path_key) in self.CRITICAL_COLUMNS.items():
            # Construct full path: section.path_key
            full_path = f"{section}.{path_key}" if path_key else section
            
            value = self._get_nested_value(rgd_entity, full_path)
            
            if value is not None:
                # Validate UUID columns (convert to string if needed)
                if col_name.endswith("_id") and value:
                    try:
                        # Ensure it's a valid UUID string
                        if isinstance(value, str):
                            uuid.UUID(value)  # Validate
                        else:
                            value = str(value)
                        extracted[col_name] = value
                        self.stats["extracted_columns"][col_name] += 1
                    except (ValueError, AttributeError):
                        self.stats["errors"].append(
                            f"Invalid UUID for {col_name}: {value}"
                        )
                # Integer columns (period_id)
                elif col_name == "period_id":
                    try:
                        extracted[col_name] = int(value)
                        self.stats["extracted_columns"][col_name] += 1
                    except (ValueError, TypeError):
                        self.stats["errors"].append(
                            f"Invalid period_id: {value}"
                        )
                else:
                    extracted[col_name] = value
                    self.stats["extracted_columns"][col_name] += 1
        
        return extracted
    
    def _build_jsonb_sections(self, rgd_entity: Dict[str, Any], extracted: Dict) -> Dict[str, Dict]:
        """
        Build JSONB section data, excluding extracted columns.
        
        Keeps all original data from RGD, minus critical columns.
        This preserves flexibility while optimizing jointure performance.
        """
        jsonb_data = {}
        
        # Iterate through all RGD entity top-level keys
        for section in self.JSONB_SECTIONS:
            section_data = rgd_entity.get(section)
            
            if section_data is None:
                continue
            
            # Deep copy to avoid modifying original
            section_copy = json.loads(json.dumps(section_data))
            
            # Remove extracted fields from this section's JSONB
            if section == "actors" and isinstance(section_copy, dict):
                # Remove extracted actor UUIDs from JSONB
                extracted_actor_keys = {
                    "player", "team", "opponent_team", "targeted_player",
                    "goalkeeper", "expected_defender_at_arrival", "previous_passer"
                }
                for key in extracted_actor_keys:
                    section_copy.pop(key, None)
            
            elif section == "phase" and isinstance(section_copy, dict):
                # Remove extracted phase UUIDs from JSONB
                extracted_phase_keys = {
                    "possession", "type_of_play", "phase_of_play", "individual_possession"
                }
                for key in extracted_phase_keys:
                    section_copy.pop(key, None)
            
            elif section == "time" and isinstance(section_copy, dict):
                # Remove period_id from time JSONB (already extracted)
                section_copy.pop("period_id", None)
            
            # Store in JSONB data (only if has remaining content)
            if section_copy:
                jsonb_data[section] = section_copy
        
        return jsonb_data
    
    def transform_entity(self, rgd_entity: Dict[str, Any]) -> EventRecord:
        """
        Transform a single RGD entity into an EventRecord.
        
        Args:
            rgd_entity: Dictionary from RGD JSON entities array
            
        Returns:
            EventRecord ready for database insertion
        """
        self.stats["total_entities"] += 1
        
        # Extract critical columns
        extracted = self._extract_critical_columns(rgd_entity)
        
        # Build JSONB sections
        jsonb_sections = self._build_jsonb_sections(rgd_entity, extracted)
        
        # Create event record
        event = EventRecord(
            # Metadata
            id=str(uuid.uuid4()),  # Generate new UUID for DB record
            game_id=self.game_id,
            created_at=self.timestamp,
            updated_at=self.timestamp,
            # Critical columns (extracted for BTREE indices)
            period_id=extracted.get("period_id"),
            player_id=extracted.get("player_id"),
            team_id=extracted.get("team_id"),
            opponent_team_id=extracted.get("opponent_team_id"),
            targeted_player_id=extracted.get("targeted_player_id"),
            goalkeeper_id=extracted.get("goalkeeper_id"),
            expected_defender_at_arrival_id=extracted.get("expected_defender_at_arrival_id"),
            previous_passer_id=extracted.get("previous_passer_id"),
            # Phase jointure columns
            possession_id=extracted.get("possession_id"),
            type_of_play_id=extracted.get("type_of_play_id"),
            phase_of_play_id=extracted.get("phase_of_play_id"),
            individual_possession_id=extracted.get("individual_possession_id"),
            # JSONB sections
            entity=jsonb_sections.get("entity"),
            time=jsonb_sections.get("time"),
            phase=jsonb_sections.get("phase"),
            spatial=jsonb_sections.get("spatial"),
            actors=jsonb_sections.get("actors"),
            receiver=jsonb_sections.get("receiver"),
            channel=jsonb_sections.get("channel"),
            adds=jsonb_sections.get("adds"),
            pass_data=jsonb_sections.get("pass"),
            custom=jsonb_sections.get("custom"),
            cross=jsonb_sections.get("cross"),
            shot=jsonb_sections.get("shot"),
            boxentry=jsonb_sections.get("boxentry"),
            finalthirdentry=jsonb_sections.get("finalthirdentry"),
            clearance=jsonb_sections.get("clearance"),
            pressure=jsonb_sections.get("pressure"),
            receivingrun=jsonb_sections.get("receivingrun"),
        )
        
        return event
    
    def transform_batch(self, rgd_entities: list) -> Tuple[list, Dict[str, Any]]:
        """
        Transform a batch of RGD entities.
        
        Args:
            rgd_entities: List of entity dictionaries from RGD JSON
            
        Returns:
            Tuple of (EventRecords list, transformation stats)
        """
        events = []
        for entity in rgd_entities:
            try:
                event = self.transform_entity(entity)
                events.append(event)
            except Exception as e:
                self.stats["errors"].append(f"Failed to transform entity: {str(e)}")
        
        return events, self.stats
    
    def to_sql_values(self, event: EventRecord) -> Dict[str, Any]:
        """
        Convert EventRecord to SQL insert dictionary.
        
        Handles:
        - UUID strings for PostgreSQL
        - None values for nullable columns
        - JSON serialization for JSONB columns
        """
        values = {
            "id": event.id,
            "game_id": event.game_id,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
            # Critical columns
            "period_id": event.period_id,
            "player_id": event.player_id,
            "team_id": event.team_id,
            "opponent_team_id": event.opponent_team_id,
            "targeted_player_id": event.targeted_player_id,
            "goalkeeper_id": event.goalkeeper_id,
            "expected_defender_at_arrival_id": event.expected_defender_at_arrival_id,
            "previous_passer_id": event.previous_passer_id,
            # Phase jointure columns
            "possession_id": event.possession_id,
            "type_of_play_id": event.type_of_play_id,
            "phase_of_play_id": event.phase_of_play_id,
            "individual_possession_id": event.individual_possession_id,
            # JSONB sections (stored as JSON strings in SQL)
            "entity": json.dumps(event.entity) if event.entity else None,
            "time": json.dumps(event.time) if event.time else None,
            "phase": json.dumps(event.phase) if event.phase else None,
            "spatial": json.dumps(event.spatial) if event.spatial else None,
            "actors": json.dumps(event.actors) if event.actors else None,
            "receiver": json.dumps(event.receiver) if event.receiver else None,
            "channel": json.dumps(event.channel) if event.channel else None,
            "adds": json.dumps(event.adds) if event.adds else None,
            "pass": json.dumps(event.pass_data) if event.pass_data else None,
            "custom": json.dumps(event.custom) if event.custom else None,
            "cross": json.dumps(event.cross) if event.cross else None,
            "shot": json.dumps(event.shot) if event.shot else None,
            "boxentry": json.dumps(event.boxentry) if event.boxentry else None,
            "finalthirdentry": json.dumps(event.finalthirdentry) if event.finalthirdentry else None,
            "clearance": json.dumps(event.clearance) if event.clearance else None,
            "pressure": json.dumps(event.pressure) if event.pressure else None,
            "receivingrun": json.dumps(event.receivingrun) if event.receivingrun else None,
        }
        
        # Remove None JSONB values to save storage
        values = {k: v for k, v in values.items() if v is not None}
        return values


