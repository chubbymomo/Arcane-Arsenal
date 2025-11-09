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


class RollHistoryComponent(ComponentTypeDefinition):
    """
    Roll History display component for character sheets.

    Provides UI for viewing dice roll history and real-time roll toasts.
    This component has no meaningful data - it's purely a UI container that
    integrates with the client-side diceRoller Alpine.js component.
    """

    type = "RollHistory"
    description = "Displays roll history and dice roll toasts on character sheet"
    schema_version = "1.0.0"
    module = "rng"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "max_visible_rolls": {
                    "type": "integer",
                    "description": "Maximum number of rolls to show in history",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 50
                }
            },
            "required": []
        }

    def get_default_data(self) -> Dict[str, Any]:
        return {
            "max_visible_rolls": 50
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Roll History appears in the RESOURCES category (Combat & Actions column)."""
        return {
            "visible": True,
            "category": "resources",
            "priority": 10,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer for Roll History with toasts."""

        # Roll History content
        # Note: The component card and title are added by the template
        html = '''
            <p x-show="history.length === 0" class="roll-history-empty">No rolls yet. Click any 🎲 button to roll!</p>

            <template x-for="(roll, index) in history" :key="index">
                <div class="roll-entry roll-success">
                    <div class="roll-label" x-text="roll.purpose || 'Roll'"></div>
                    <div class="roll-total"
                         :class="{
                             'critical-success': roll.critical_success,
                             'critical-failure': roll.critical_failure
                         }"
                         x-text="roll.total">
                    </div>
                    <div class="roll-breakdown" x-text="roll.breakdown"></div>
                </div>
            </template>

            <!-- Dice roll toasts (global floating UI) -->
            <!-- Rolling indicator toast -->
            <div x-show="rolling"
                 x-transition.scale.90.opacity
                 x-cloak
                 class="roll-toast"
                 style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
                <div class="roll-toast-content">
                    <div class="roll-status">🎲 Rolling...</div>
                </div>
            </div>

            <!-- Result toast (shows after rolling completes) -->
            <div x-show="showResult"
                 x-transition.scale.90.opacity.duration.500ms
                 x-cloak
                 class="roll-toast"
                 style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
                <div class="roll-toast-content">
                    <div class="roll-toast-label" x-text="result?.purpose || 'Roll'"></div>
                    <div class="roll-toast-total"
                         :class="{
                             'critical-success': result?.critical_success,
                             'critical-failure': result?.critical_failure
                         }"
                         x-text="result?.total">
                    </div>
                    <div class="roll-toast-breakdown" x-text="result?.breakdown"></div>
                </div>
            </div>
        '''

        return html
