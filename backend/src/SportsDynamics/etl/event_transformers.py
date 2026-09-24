#!/usr/bin/env python3
"""
Event Transformers for Hybrid Schema

Converts RGD JSON data to specific event table structures.
All transformers follow the same pattern as RGDToEventsTransformer.

Tables:
1. BallInPlay - Tracking when ball is in/out of play
2. Card - Red/yellow cards
3. Foul - Fouls and rule violations
4. GoalKick - Goalkeeper kick-outs
5. Goals - All goals scored
6. IndividualPossession - Individual player possession tracking
7. Kickoff - Match/period kickoffs
8. Offside - Offside incidents
9. PhaseOfPlay - Possession phases
10. PossessionCollective - Team possession phases
11. Setpieces - Set pieces (corners, free kicks)
12. TypeOfPlay - Classification of play type
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class BaseEventTransformer:
    """
    Base class for all event transformers.
    Provides common extraction patterns and JSONB structuring.
    """
    
    def __init__(self, game_id: str):
        self.game_id = game_id
    
    @staticmethod
    def _get_nested_value(obj: Dict, path: str, default=None) -> Any:
        """Navigate nested dict using dot notation: 'entity.type.name'"""
        keys = path.split('.')
        result = obj
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return default
        return result if result is not None else default
    
    def transform_batch(self, events: List[Dict]) -> tuple:
        """Transform batch of RGD events. Returns (records, stats_dict)"""
        records = []
        stats = {
            "total_events": len(events),
            "extracted_columns": {},
            "errors": [],
            "skipped": []
        }
        
        for event in events:
            try:
                record = self._transform_single(event)
                if record:
                    records.append(record)
            except Exception as e:
                stats["errors"].append(f"{self._get_table_name()}: {str(e)}")
        
        return records, stats
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        """Transform single event - override in subclass"""
        raise NotImplementedError
    
    def _get_table_name(self) -> str:
        """Return target table name - override in subclass"""
        raise NotImplementedError


class BallInPlayTransformer(BaseEventTransformer):
    """
    BallInPlay Table Transformer
    
    Critical columns:
    - game_id (FK to games)
    - period_id (INDEX)
    - team_id (FK to teams) - team with possession or playing ball
    
    JSONB sections:
    - entity (entityType: "ball_in_play", duration, outcome)
    - temporal (start_time, end_time, time_clock)
    - status (in_play, outcome: IN/OUT)
    """
    
    def _get_table_name(self) -> str:
        return "ball_in_play"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        # Filter for ball in/out play events only
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type not in ["ball_in_play", "ball_out", "ball_recovery"]:
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "team_id": self._get_nested_value(event, "actors.team"),
            
            # JSONB: entity section
            "entity": json.dumps({
                "entityType": entity_type,
                "duration": self._get_nested_value(event, "duration"),
                "sequence_id": self._get_nested_value(event, "sequence_id"),
                "version": 1
            }),
            
            # JSONB: temporal section
            "temporal": json.dumps({
                "period_id": self._get_nested_value(event, "time.period_id"),
                "seconds_elapsed": self._get_nested_value(event, "time.seconds_elapsed"),
                "time_clock": self._get_nested_value(event, "time.time_clock"),
                "start": self._get_nested_value(event, "start")
            }),
            
            # JSONB: status section
            "status": json.dumps({
                "in_play": entity_type == "ball_in_play",
                "outcome": self._get_nested_value(event, "outcome", "UNKNOWN")
            })
        }


class CardTransformer(BaseEventTransformer):
    """
    Card Table Transformer (Red/Yellow cards)
    
    Critical columns:
    - game_id (FK)
    - period_id (INDEX)
    - player_id (FK to players) - player receiving card
    - team_id (FK to teams) - team of player
    """
    
    def _get_table_name(self) -> str:
        return "card"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "card":
            return None
        
        card_type = self._get_nested_value(event, "card.card_type", "UNKNOWN")
        if card_type not in ["RED", "YELLOW"]:
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "player_id": self._get_nested_value(event, "actors.player"),
            "team_id": self._get_nested_value(event, "actors.team"),
            
            "entity": json.dumps({
                "entityType": "card",
                "card_type": card_type,
                "reason": self._get_nested_value(event, "card.reason", "UNKNOWN")
            }),
            
            "time": json.dumps({
                "period_id": self._get_nested_value(event, "time.period_id"),
                "seconds_elapsed": self._get_nested_value(event, "time.seconds_elapsed"),
                "time_clock": self._get_nested_value(event, "time.time_clock")
            }),
            
            "spatial": json.dumps({}),
            
            "actors": json.dumps({
                "player": self._get_nested_value(event, "actors.player"),
                "team": self._get_nested_value(event, "actors.team")
            }),
            
            "card": json.dumps({
                "card_type": card_type,
                "offense_type": self._get_nested_value(event, "card.offense_type"),
                "reason": self._get_nested_value(event, "card.reason", "UNKNOWN")
            })
        }


class FoulTransformer(BaseEventTransformer):
    """Foul Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "foul"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "foul":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "player_id": self._get_nested_value(event, "actors.player"),
            "team_id": self._get_nested_value(event, "actors.team"),
            
            "entity": json.dumps({
                "entityType": "foul",
                "foul_type": self._get_nested_value(event, "foul.foul_type", "UNKNOWN")
            }),
            
            "temporal": json.dumps({
                "period_id": self._get_nested_value(event, "time.period_id"),
                "seconds_elapsed": self._get_nested_value(event, "time.seconds_elapsed")
            }),
            
            "context": json.dumps({
                "affected_player": self._get_nested_value(event, "actors.targeted_player"),
                "location": self._get_nested_value(event, "spatial.startX")
            })
        }


class GoalKickTransformer(BaseEventTransformer):
    """GoalKick Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "goalkick"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "goal_kick":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "team_id": self._get_nested_value(event, "actors.team"),
            
            "entity": json.dumps({
                "entityType": "goal_kick",
                "kicker_type": "goalkeeper"
            }),
            
            "temporal": json.dumps({
                "seconds_elapsed": self._get_nested_value(event, "time.seconds_elapsed"),
                "time_clock": self._get_nested_value(event, "time.time_clock")
            }),
            
            "kickout": json.dumps({
                "goalkeeper_id": self._get_nested_value(event, "actors.goalkeeper"),
                "destination": {
                    "x": self._get_nested_value(event, "spatial.endX"),
                    "y": self._get_nested_value(event, "spatial.endY")
                }
            })
        }


class GoalsTransformer(BaseEventTransformer):
    """Goals Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "goals"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "goal":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "player_id": self._get_nested_value(event, "actors.player"),
            "team_id": self._get_nested_value(event, "actors.team"),
            
            "entity": json.dumps({
                "entityType": "goal",
                "goal_type": self._get_nested_value(event, "goal.goalType", "open_play"),
                "body_part": self._get_nested_value(event, "goal.bodyPart", "foot")
            }),
            
            "time": json.dumps({
                "period_id": self._get_nested_value(event, "time.period_id"),
                "seconds_elapsed": self._get_nested_value(event, "time.seconds_elapsed"),
                "time_clock": self._get_nested_value(event, "time.time_clock")
            }),
            
            "spatial": json.dumps({}),  # Empty spatial for goals
            
            "actors": json.dumps({
                "player": self._get_nested_value(event, "actors.player"),
                "team": self._get_nested_value(event, "actors.team"),
                "assister": self._get_nested_value(event, "actors.assister"),
                "goalkeeper": self._get_nested_value(event, "actors.goalkeeper")
            }),
            
            "shot": json.dumps({
                "assister_id": self._get_nested_value(event, "actors.assister"),
                "is_penalty": self._get_nested_value(event, "goal.is_penalty", False),
                "is_own_goal": self._get_nested_value(event, "goal.is_own_goal", False),
                "goalkeeper_id": self._get_nested_value(event, "actors.goalkeeper")
            })
        }


class IndividualPossessionTransformer(BaseEventTransformer):
    """IndividualPossession Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "individual_possession"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "individual_possession":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "player_id": self._get_nested_value(event, "actors.player"),
            "team_id": self._get_nested_value(event, "actors.team"),
            
            "entity": json.dumps({
                "entityType": "individual_possession",
                "possession_id": self._get_nested_value(event, "phase.individual_possession")
            }),
            
            "temporal": json.dumps({
                "start_time": self._get_nested_value(event, "time.time_clock"),
                "duration": self._get_nested_value(event, "duration", 0)
            }),
            
            "possession_data": json.dumps({
                "touches": self._get_nested_value(event, "possession.touches", 0),
                "distance_covered": self._get_nested_value(event, "spatial.distance", 0)
            })
        }


class KickoffTransformer(BaseEventTransformer):
    """Kickoff Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "kickoff"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "kickoff":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            
            "entity": json.dumps({
                "entityType": "kickoff",
                "period_start": self._get_nested_value(event, "time.period_id") == 1
            }),
            
            "temporal": json.dumps({
                "period_id": self._get_nested_value(event, "time.period_id"),
                "time_clock": self._get_nested_value(event, "time.time_clock", "00:00")
            }),
            
            "kickoff_details": json.dumps({
                "kicking_team": self._get_nested_value(event, "actors.team"),
                "receiving_team": self._get_nested_value(event, "actors.opponent_team")
            })
        }


class OffsideTransformer(BaseEventTransformer):
    """Offside Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "offside"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "offside":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "player_id": self._get_nested_value(event, "actors.player"),
            "team_id": self._get_nested_value(event, "actors.team"),
            
            "entity": json.dumps({
                "entityType": "offside",
                "offside_called": True
            }),
            
            "temporal": json.dumps({
                "seconds_elapsed": self._get_nested_value(event, "time.seconds_elapsed"),
                "time_clock": self._get_nested_value(event, "time.time_clock")
            }),
            
            "offside_data": json.dumps({
                "player_position": self._get_nested_value(event, "spatial.startX"),
                "ball_position": self._get_nested_value(event, "spatial.endX")
            })
        }


class PhaseOfPlayTransformer(BaseEventTransformer):
    """PhaseOfPlay Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "phase_of_play"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "phase_of_play":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "team_id": self._get_nested_value(event, "actors.team"),
            "possession_id": self._get_nested_value(event, "phase.possession"),
            "phase_of_play_id": self._get_nested_value(event, "phase.phase_of_play"),
            
            "entity": json.dumps({
                "entityType": "phase_of_play",
                "phase_id": self._get_nested_value(event, "phase.phase_of_play")
            }),
            
            "temporal": json.dumps({
                "start": self._get_nested_value(event, "time.time_clock"),
                "duration": self._get_nested_value(event, "duration", 0)
            }),
            
            "phase_data": json.dumps({
                "team_in_possession": self._get_nested_value(event, "actors.team"),
                "passes_in_phase": self._get_nested_value(event, "phase.passes", 0)
            })
        }


class PossessionCollectiveTransformer(BaseEventTransformer):
    """PossessionCollective Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "possession_collective"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "possession_collective":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            "team_id": self._get_nested_value(event, "actors.team"),
            "possession_id": self._get_nested_value(event, "phase.possession"),
            
            "entity": json.dumps({
                "entityType": "possession_collective",
                "possession_sequence": self._get_nested_value(event, "sequence_id")
            }),
            
            "temporal": json.dumps({
                "start_time": self._get_nested_value(event, "time.time_clock"),
                "duration": self._get_nested_value(event, "duration", 0),
                "period_id": self._get_nested_value(event, "time.period_id")
            }),
            
            "possession_stats": json.dumps({
                "total_passes": self._get_nested_value(event, "possession.passes", 0),
                "distance_covered": self._get_nested_value(event, "spatial.distance", 0),
                "final_action": self._get_nested_value(event, "possession.final_action", "UNKNOWN")
            })
        }


class SetpiecesTransformer(BaseEventTransformer):
    """Setpieces Table Transformer (corners, free kicks, throw-ins)"""
    
    def _get_table_name(self) -> str:
        return "setpieces"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type not in ["corner", "free_kick", "throw_in", "setpiece"]:
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            
            "entity": json.dumps({
                "entityType": entity_type,
                "setpiece_type": entity_type.upper()
            }),
            
            "temporal": json.dumps({
                "seconds_elapsed": self._get_nested_value(event, "time.seconds_elapsed"),
                "time_clock": self._get_nested_value(event, "time.time_clock")
            }),
            
            "setpiece_details": json.dumps({
                "kicking_team": self._get_nested_value(event, "actors.team"),
                "taker": self._get_nested_value(event, "actors.player"),
                "location_x": self._get_nested_value(event, "spatial.startX"),
                "location_y": self._get_nested_value(event, "spatial.startY")
            })
        }


class TypeOfPlayTransformer(BaseEventTransformer):
    """TypeOfPlay Table Transformer"""
    
    def _get_table_name(self) -> str:
        return "type_of_play"
    
    def _transform_single(self, event: Dict) -> Optional[Dict]:
        entity_type = self._get_nested_value(event, "entity.entityType")
        if entity_type != "type_of_play":
            return None
        
        return {
            "id": str(uuid.uuid4()),
            "game_id": self.game_id,
            "period_id": self._get_nested_value(event, "time.period_id"),
            
            "entity": json.dumps({
                "entityType": "type_of_play",
                "classification": self._get_nested_value(event, "type_of_play.classification", "OPEN_PLAY")
            }),
            
            "temporal": json.dumps({
                "period_id": self._get_nested_value(event, "time.period_id"),
                "sequence": self._get_nested_value(event, "sequence_id")
            }),
            
            "play_type_data": json.dumps({
                "play_type": self._get_nested_value(event, "type_of_play.type", "UNKNOWN"),
                "team": self._get_nested_value(event, "actors.team")
            })
        }


# Factory function to get appropriate transformer
def get_transformer(table_name: str, game_id: str) -> BaseEventTransformer:
    """Get transformer instance for specific event table"""
    transformers = {
        "ball_in_play": BallInPlayTransformer,
        "card": CardTransformer,
        "foul": FoulTransformer,
        "goalkick": GoalKickTransformer,
        "goals": GoalsTransformer,
        "individual_possession": IndividualPossessionTransformer,
        "kickoff": KickoffTransformer,
        "offside": OffsideTransformer,
        "phase_of_play": PhaseOfPlayTransformer,
        "possession_collective": PossessionCollectiveTransformer,
        "setpieces": SetpiecesTransformer,
        "type_of_play": TypeOfPlayTransformer,
    }
    
    transformer_class = transformers.get(table_name.lower())
    if not transformer_class:
        raise ValueError(f"Unknown transformer for table: {table_name}")
    
    return transformer_class(game_id)
