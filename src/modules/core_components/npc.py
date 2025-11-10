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
    - Has NPC + CharacterDetails + Identity: Named NPC with race and personality
    - Has NPC + CharacterDetails (with class): NPC with class/level mechanics
    - Has PlayerCharacter + CharacterDetails: Player-controlled character
    - No NPC or PlayerCharacter: Monster, item, location, etc.

This component works with:
    - Identity: NPC description (narrative data)
    - CharacterDetails: Race (required for all NPCs), class/level (optional for mechanically-defined NPCs)
    - Position: NPC location in the world
    - Conversation: For NPCs the player can talk to

Examples:
    # Tavern keeper (simple NPC - race but no class)
    engine.add_component(keeper_id, 'Identity', {
        'description': 'A grizzled dwarf who runs the tavern'
    })
    engine.add_component(keeper_id, 'CharacterDetails', {
        'race': 'dwarf'
    })
    engine.add_component(keeper_id, 'NPC', {
        'occupation': 'tavern keeper',
        'disposition': 'friendly',
        'met_player': False
    })

    # Enemy wizard (NPC with class/level for combat mechanics)
    engine.add_component(wizard_id, 'Identity', {
        'description': 'A dark wizard who commands shadow magic'
    })
    engine.add_component(wizard_id, 'CharacterDetails', {
        'race': 'human',
        'character_class': 'wizard',
        'level': 8
    })
    engine.add_component(wizard_id, 'NPC', {
        'occupation': 'evil wizard',
        'disposition': 'hostile',
        'met_player': True
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
            occupation: NPC's occupation or role
            disposition: How the NPC feels toward the player
            dialogue_state: Current state in dialogue tree (default: 'initial')
            met_player: Whether the NPC has met the player (default: False)

        Note: Race is stored in CharacterDetails component, not here.
        All NPCs should have CharacterDetails with at least race defined.
        """
        return {
            "type": "object",
            "properties": {
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
