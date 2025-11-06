"""
Component definitions for RNG module.
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class LuckComponent(ComponentTypeDefinition):
    """
    Luck modifier component - affects all rolls for this entity.

    Can represent:
    - Character traits (Lucky feat, Halfling luck)
    - Temporary buffs/debuffs
    - Cursed items
    """

    type = "Luck"
    description = "Modifies dice rolls with luck bonuses or advantage mechanics"
    schema_version = "1.0.0"
    module = "rng"

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """Validate advantage_on/disadvantage_on arrays against registered roll types."""
        # Get registered roll types
        valid_types = {rt['type'] for rt in engine.storage.get_roll_types()}

        # Validate advantage_on
        advantage_on = data.get('advantage_on', [])
        for roll_type in advantage_on:
            if roll_type not in valid_types:
                raise ValueError(
                    f"Invalid roll type in advantage_on: '{roll_type}'. "
                    f"Must be one of: {', '.join(sorted(valid_types))}. "
                    f"Query /api/roll_types to see all valid types."
                )

        # Validate disadvantage_on
        disadvantage_on = data.get('disadvantage_on', [])
        for roll_type in disadvantage_on:
            if roll_type not in valid_types:
                raise ValueError(
                    f"Invalid roll type in disadvantage_on: '{roll_type}'. "
                    f"Must be one of: {', '.join(sorted(valid_types))}. "
                    f"Query /api/roll_types to see all valid types."
                )

        return True

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "global_bonus": {
                    "type": "integer",
                    "description": "Flat bonus/penalty to all rolls",
                    "default": 0
                },
                "advantage_on": {
                    "type": "array",
                    "description": "Roll types that get advantage. Must be registered roll types (see engine.storage.get_roll_types())",
                    "items": {"type": "string"},
                    "default": []
                },
                "disadvantage_on": {
                    "type": "array",
                    "description": "Roll types that get disadvantage. Must be registered roll types",
                    "items": {"type": "string"},
                    "default": []
                },
                "reroll_ones": {
                    "type": "boolean",
                    "description": "Reroll natural 1s (Halfling Luck)",
                    "default": False
                },
                "critical_range": {
                    "type": "integer",
                    "description": "Crit on this number or higher (20 = normal, 19 = improved)",
                    "minimum": 2,
                    "maximum": 20,
                    "default": 20
                }
            },
            "required": []
        }

    def get_default_data(self) -> Dict[str, Any]:
        return {
            "global_bonus": 0,
            "advantage_on": [],
            "disadvantage_on": [],
            "reroll_ones": False,
            "critical_range": 20
        }


class RollModifierComponent(ComponentTypeDefinition):
    """
    Specific roll modifier component - affects certain types of rolls.

    Examples:
    - +3 to attack rolls (from magic weapon)
    - +2 to saving throws (from cloak of protection)
    - -1 to stealth (from heavy armor)
    """

    type = "RollModifier"
    description = "Modifies specific types of dice rolls"
    schema_version = "1.0.0"
    module = "rng"

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """Validate modifier_type against registered roll types."""
        modifier_type = data.get('modifier_type')
        if not modifier_type:
            raise ValueError("modifier_type is required")

        # Get registered roll types
        valid_types = {rt['type'] for rt in engine.storage.get_roll_types()}

        if modifier_type not in valid_types:
            raise ValueError(
                f"Invalid modifier_type '{modifier_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}. "
                f"Query /api/roll_types to see all valid types."
            )

        return True

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "modifier_type": {
                    "type": "string",
                    "description": "What this modifier affects. Must be a registered roll type (see engine.storage.get_roll_types())",
                    "examples": ["attack", "damage", "saving_throw", "skill_check", "initiative"]
                },
                "bonus": {
                    "type": "integer",
                    "description": "Numeric bonus (can be negative)"
                },
                "source": {
                    "type": "string",
                    "description": "What grants this modifier (item name, spell name, etc.)",
                    "default": "Unknown"
                },
                "conditions": {
                    "type": "object",
                    "description": "Optional conditions for when this modifier applies",
                    "properties": {
                        "only_if": {
                            "type": "string",
                            "description": "Condition that must be true"
                        },
                        "against": {
                            "type": "array",
                            "description": "Enemy types this affects (e.g., ['undead', 'fiends'])",
                            "items": {"type": "string"}
                        }
                    },
                    "default": {}
                }
            },
            "required": ["modifier_type", "bonus"]
        }
