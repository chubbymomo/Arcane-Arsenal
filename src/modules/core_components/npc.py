"""
NPC Component.

Marks an entity as a Non-Player Character and tracks their disposition
toward the player.

Usage:
    # Create an NPC with neutral disposition
    engine.add_component(npc_id, 'NPC', {
        'disposition': 'neutral',
        'met_player': False
    })

    # Query for all NPCs
    npcs = engine.query_entities(['NPC'])

    # Query for hostile NPCs
    hostile = engine.query_entities(['NPC'])
    hostile = [e for e in hostile if e.NPC['disposition'] == 'hostile']

Entity Type by Components:
    - Has NPC + Identity: Named NPC with personality
    - Has NPC + CharacterDetails: NPC with class/level mechanics
    - Has PlayerCharacter: Player-controlled character
    - No NPC or PlayerCharacter: Monster, item, location, etc.

This component works with:
    - Identity: NPC description, race, occupation
    - CharacterDetails: Class, level (for mechanically-defined NPCs)
    - Position: NPC location in the world
    - Conversation: For NPCs the player can talk to

Examples:
    # Tavern keeper (simple NPC)
    engine.add_component(keeper_id, 'NPC', {
        'disposition': 'friendly',
        'met_player': False
    })
    engine.add_component(keeper_id, 'Identity', {
        'description': 'A grizzled dwarf who runs the tavern',
        'race': 'dwarf',
        'occupation': 'tavern keeper'
    })

    # Enemy wizard (NPC with class/level)
    engine.add_component(wizard_id, 'NPC', {
        'disposition': 'hostile',
        'met_player': True
    })
    engine.add_component(wizard_id, 'Identity', {
        'description': 'A dark wizard who commands shadow magic',
        'race': 'human',
        'occupation': 'evil wizard'
    })
    engine.add_component(wizard_id, 'CharacterDetails', {
        'character_class': 'wizard',
        'level': 8,
        'race': 'human'
    })
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class NPCComponent(ComponentTypeDefinition):
    """NPC marker component definition."""

    type = 'NPC'
    description = 'Marks an entity as a non-player character with disposition'
    schema_version = '1.0.0'
    module = 'core_components'

    def get_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for NPC component.

        Properties:
            race: NPC's race (human, elf, dwarf, etc.)
            occupation: NPC's occupation or role
            disposition: How the NPC feels toward the player
            dialogue_state: Current state in dialogue tree (default: 'initial')
            met_player: Whether the NPC has met the player (default: False)
        """
        return {
            "type": "object",
            "properties": {
                "race": {
                    "type": "string",
                    "description": "NPC's race (human, elf, dwarf, etc.)"
                },
                "occupation": {
                    "type": "string",
                    "description": "NPC's occupation or role (blacksmith, guard, merchant, etc.)"
                },
                "disposition": {
                    "type": "string",
                    "enum": ["friendly", "neutral", "hostile", "fearful", "admiring"],
                    "description": "NPC's attitude toward the player"
                },
                "dialogue_state": {
                    "type": "string",
                    "description": "Current dialogue state",
                    "default": "initial"
                },
                "met_player": {
                    "type": "boolean",
                    "description": "Whether NPC has met the player",
                    "default": False
                }
            },
            "required": ["disposition"]
        }

    def get_default_data(self) -> Dict[str, Any]:
        """Get default data for new NPC components."""
        return {
            "disposition": "neutral",
            "dialogue_state": "initial",
            "met_player": False
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """NPCs show their disposition on character sheets."""
        return {
            "visible": True,
            "category": "info"
        }
