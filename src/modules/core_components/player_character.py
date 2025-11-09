"""
PlayerCharacter Component.

A marker component that identifies an entity as a player-controlled character.
This component can optionally store AI intro state.

Usage:
    # Mark entity as player character
    engine.add_component(char_id, 'PlayerCharacter', {})

    # Mark entity as player character needing AI intro
    engine.add_component(char_id, 'PlayerCharacter', {'needs_ai_intro': True})

    # Query for all player characters
    player_characters = engine.query_entities(['PlayerCharacter'])

Entity Type by Components:
    - Has PlayerCharacter: This is a player-controlled character
    - No PlayerCharacter: NPC, monster, item, location, etc.

This component works with:
    - Identity: Character description
    - Position: Character location
    - (Phase 2) CharacterStats: Health, level, etc.
    - (Phase 2) Inventory: Items carried

Examples:
    # Player character
    engine.add_component(hero_id, 'PlayerCharacter', {})
    engine.add_component(hero_id, 'Identity', {'description': 'A brave hero'})
    engine.add_component(hero_id, 'Position', {'x': 0, 'y': 0, 'z': 0, 'region': 'world'})

    # NPC (no PlayerCharacter component)
    engine.add_component(npc_id, 'Identity', {'description': 'A friendly shopkeeper'})
    engine.add_component(npc_id, 'Position', {'x': 10, 'y': 10, 'z': 0, 'region': 'town'})
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class PlayerCharacterComponent(ComponentTypeDefinition):
    """PlayerCharacter marker component definition."""

    type = 'PlayerCharacter'
    description = 'Marks an entity as a player-controlled character'
    schema_version = '1.0.0'
    module = 'core_components'

    def get_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for PlayerCharacter component.

        This is a pure marker component with no properties.
        """
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
