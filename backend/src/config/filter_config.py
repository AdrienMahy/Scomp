"""Query filter configuration management"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

class QueryFilterConfig:
    """Manage GraphQL query filter configurations"""
    
    def __init__(self):
        """Load filter configuration"""
        config_file = Path(__file__).parent / "graphql_filters.json"
        
        if not config_file.exists():
            raise FileNotFoundError(f"GraphQL filters config not found: {config_file}")
        
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        # Load predefined filters
        predefined_file = Path(__file__).parent / "predefined_filters.json"
        if predefined_file.exists():
            with open(predefined_file, 'r') as f:
                self.predefined = json.load(f)
        else:
            self.predefined = {}
    
    def get_query_config(self, query_name: str) -> Dict[str, Any]:
        """Get configuration for a specific query"""
        query_key = query_name.lower()
        if query_key not in self.config.get("queries", {}):
            raise ValueError(f"Query '{query_name}' not found in configuration")
        
        return self.config["queries"][query_key]
    
    def get_available_filters(self, query_name: str) -> list:
        """Get list of available filters for a query"""
        config = self.get_query_config(query_name)
        return config.get("filters", {}).get("available_filters", [])
    
    def get_example_filters(self, query_name: str) -> Dict[str, Any]:
        """Get example filters for a query"""
        config = self.get_query_config(query_name)
        return config.get("example_filters", {})
    
    def get_pagination_config(self, query_name: str) -> Dict[str, Any]:
        """Get pagination configuration for a query"""
        config = self.get_query_config(query_name)
        return config.get("pagination", {})
    
    def build_filter_payload(self, query_name: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build complete filter payload for a query
        
        Args:
            query_name: Name of the query
            filters: Custom filters to apply
            
        Returns:
            Complete filter payload ready for API call
        """
        config = self.get_query_config(query_name)
        
        # Start with example filters
        payload = config.get("example_filters", {}).copy()
        
        # Override with custom filters
        if filters:
            payload.update(filters)
        
        return payload
    
    def list_all_queries(self) -> list:
        """List all available queries"""
        return list(self.config.get("queries", {}).keys())
    
    def get_filter_operators(self) -> Dict[str, Any]:
        """Get all available filter operators"""
        return self.config.get("filter_operators", {})
    
    def validate_filter(self, query_name: str, filter_key: str) -> bool:
        """Check if a filter is valid for a query"""
        available = self.get_available_filters(query_name)
        return filter_key in available
    
    def get_predefined_filters(self, query_name: str) -> Dict[str, Any]:
        """Get predefined filter schema for a query"""
        query_key = query_name.lower()
        if query_key not in self.predefined.get("queries", {}):
            return {}
        return self.predefined["queries"][query_key].get("filters", {})
    
    def build_payload_from_values(self, query_name: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build GraphQL filter payload from simple values
        
        Example:
            values = {
                "available": True,
                "competition_id": "comp-123",
                "season_id": "2024"
            }
            payload = config.build_payload_from_values("get_games", values)
            # Returns: {
            #   "available": {"equals": True},
            #   "competition": {"id": {"equals": "comp-123"}},
            #   "season": {"id": {"equals": "2024"}}
            # }
        
        Args:
            query_name: Name of the query
            values: Dict with simple filter values
            
        Returns:
            GraphQL filter payload ready for API
        """
        predefined = self.get_predefined_filters(query_name)
        payload = {}
        
        for filter_key, filter_value in values.items():
            if filter_value is None:
                continue
            
            # Get filter definition
            if filter_key not in predefined:
                raise ValueError(f"Unknown filter '{filter_key}' for query '{query_name}'")
            
            filter_def = predefined[filter_key]
            graphql_path = filter_def.get("graphql_path")
            operator = filter_def.get("operator", "equals")
            
            # Build nested GraphQL structure
            # Example: "competition.id" → {"competition": {"id": {"equals": value}}}
            self._set_nested_value(payload, graphql_path, operator, filter_value)
        
        return payload
    
    def _set_nested_value(self, obj: dict, path: str, operator: str, value: Any):
        """
        Set nested value in dict using dot notation
        
        Example:
            _set_nested_value(obj, "competition.id", "equals", "123")
            obj becomes: {"competition": {"id": {"equals": "123"}}}
        """
        parts = path.split(".")
        current = obj
        
        # Navigate/create nested structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set final value with operator
        final_key = parts[-1]
        current[final_key] = {operator: value}
    
    def get_required_filters(self, query_name: str) -> list:
        """Get list of required filters for a query"""
        predefined = self.get_predefined_filters(query_name)
        return [k for k, v in predefined.items() if v.get("required", False)]
    
    def validate_required_filters(self, query_name: str, values: Dict[str, Any]) -> tuple:
        """
        Validate that all required filters are provided
        
        Returns:
            (is_valid: bool, missing_filters: list)
        """
        required = self.get_required_filters(query_name)
        missing = [f for f in required if f not in values or values[f] is None]
        return len(missing) == 0, missing


# Singleton instance
_filter_config_instance = None

def get_filter_config() -> QueryFilterConfig:
    """Get or create filter config instance"""
    global _filter_config_instance
    if _filter_config_instance is None:
        _filter_config_instance = QueryFilterConfig()
    return _filter_config_instance
