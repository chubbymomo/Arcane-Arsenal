"""
Location Component.

Marks an entity as a location/place in the game world and stores
location-specific data like region, features, and visit status.

Usage:
    # Create a location
    engine.add_component(location_id, 'Location', {
        'region': 'The Shadowfen Marshes',
        'features': ['Ancient ruins', 'Foggy waters', 'Twisted trees'],
        'visited': False
    })

    # Query for all locations
    locations = engine.query_entities(['Location'])

    # Query for locations in a specific region
    marshes = [loc for loc in locations
               if loc.Location['region'] == 'The Shadowfen Marshes']

Entity Type by Components:
    - Has Location + Identity: Named place with description
    - Has Position: Positioned entity (character, item, etc.)
    - Has both Location and Position: Debatable - locations might not need Position

This component works with:
    - Identity: Location name and detailed description
    - Position: Characters/items positioned at this location (via region)
    - Container: For locations that can hold items

Examples:
    # A tavern
    engine.add_component(tavern_id, 'Location', {
        'region': 'Ironpeak Town',
        'features': ['Warm hearth', 'Long oak bar', 'Private rooms upstairs'],
        'visited': True
    })
    engine.add_component(tavern_id, 'Identity', {
        'description': 'The Iron Flagon, a bustling tavern in the heart of town'
    })

    # A dangerous dungeon
    engine.add_component(dungeon_id, 'Location', {
        'region': 'The Underdark Depths',
        'features': ['Dark passages', 'Ancient traps', 'Monster lairs'],
        'visited': False
    })
    engine.add_component(dungeon_id, 'Identity', {
        'description': 'The Tomb of the Fallen King, sealed for a thousand years'
    })
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class LocationComponent(ComponentTypeDefinition):
    """Location marker component definition."""

    type = 'Location'
    description = 'Marks an entity as a location with region and features'
    schema_version = '1.0.0'
    module = 'core_components'

    def get_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for Location component.

        Properties:
            region: Broader geographic region (e.g., 'Shadowfen Marshes')
            features: Notable features of the location (array of strings)
            visited: Whether the player has visited this location
        """
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "Broader geographic region"
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Notable features of this location",
                    "default": []
                },
                "visited": {
                    "type": "boolean",
                    "description": "Has player visited this location",
                    "default": False
                }
            },
            "required": ["region"]
        }

    def get_default_data(self) -> Dict[str, Any]:
        """Get default data for new Location components."""
        return {
            "features": [],
            "visited": False
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Locations don't appear on character sheets."""
        return {
            "visible": False,
            "category": "misc"
        }
