"""
Location Component.

Marks an entity as a location/place in the game world. Locations are entities
that other entities can be positioned within using entity-based hierarchical positioning.

Usage:
    # Create a location with hierarchical positioning
    # Locations need both Location (marker) and Position (where they are) components

    engine.add_component(tavern_id, 'Location', {
        'location_type': 'tavern',
        'features': ['Warm hearth', 'Long oak bar', 'Private rooms upstairs'],
        'visited': False
    })
    engine.add_component(tavern_id, 'Position', {
        'region': 'The Shadowfen Marshes'  # Broader area this location is in
    })
    engine.add_component(tavern_id, 'Identity', {
        'description': 'The Iron Flagon, a bustling tavern'
    })

    # Now position NPCs/items AT this location using entity reference
    engine.add_component(npc_id, 'Position', {
        'region': tavern_id  # Entity reference! NPC is in the tavern
    })

Entity-Based Hierarchical Positioning:
    - Locations are entities with Location + Position + Identity components
    - Position.region can be:
      * Named region string (e.g., "The Shadowfen Marshes") for top-level locations
      * Entity ID (e.g., "entity_tavern_123") for nested positioning
    - NPCs/items positioned AT locations use the location's entity ID in Position.region
    - Nearby queries find entities with Position.region == location_entity_id

This component works with:
    - Identity: Location name and detailed description
    - Position: Where the location itself is (in broader region or nested in another location)
    - Container: For locations that can hold items physically

Examples:
    # Region-level location (in named region)
    engine.add_component(tavern_id, 'Location', {'location_type': 'tavern', 'visited': True})
    engine.add_component(tavern_id, 'Position', {'region': 'The Shadowfen Marshes'})

    # NPC positioned at the tavern (entity-based)
    engine.add_component(npc_id, 'NPC', {'disposition': 'friendly'})
    engine.add_component(npc_id, 'Position', {'region': tavern_id})

    # Nested location (room inside tavern)
    engine.add_component(room_id, 'Location', {'location_type': 'room', 'visited': False})
    engine.add_component(room_id, 'Position', {'region': tavern_id})  # Room is IN tavern
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
            location_type: Type of location (tavern, dungeon, town, etc.)
            features: Notable features of the location (array of strings)
            visited: Whether the player has visited this location

        Note: Use Position component to specify WHERE the location is.
        Position.region can be a named region string or parent location entity ID.
        """
        return {
            "type": "object",
            "properties": {
                "location_type": {
                    "type": "string",
                    "description": "Type of location (tavern, dungeon, forest, town, etc.)"
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
            "required": ["location_type"]
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
