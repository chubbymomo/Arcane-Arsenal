"""
Attributes Component for Generic Fantasy Module.

Provides core ability scores (Strength, Dexterity, Constitution,
Intelligence, Wisdom, Charisma) commonly used in fantasy RPGs.
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class AttributesComponent(ComponentTypeDefinition):
    """
    Core ability scores for fantasy characters.

    Tracks six attributes (STR, DEX, CON, INT, WIS, CHA) with values typically
    ranging from 1-20 in most fantasy systems. Modifiers are calculated as:
    (attribute - 10) // 2
    """

    type = "Attributes"
    description = "Core ability scores (STR, DEX, CON, INT, WIS, CHA)"
    schema_version = "1.0.0"
    module = "generic_fantasy"

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for attributes."""
        return {
            "type": "object",
            "properties": {
                "strength": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Physical power and muscle"
                },
                "dexterity": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Agility, reflexes, and balance"
                },
                "constitution": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Endurance and health"
                },
                "intelligence": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Reasoning and memory"
                },
                "wisdom": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Awareness and insight"
                },
                "charisma": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Force of personality and leadership"
                }
            },
            "required": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Return UI metadata for attributes."""
        return {
            "strength": {
                "label": "Strength (STR)",
                "widget": "number",
                "order": 0,
                "help_text": "Physical power, muscle, carrying capacity",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Physical Attributes"
            },
            "dexterity": {
                "label": "Dexterity (DEX)",
                "widget": "number",
                "order": 1,
                "help_text": "Agility, reflexes, balance, coordination",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Physical Attributes"
            },
            "constitution": {
                "label": "Constitution (CON)",
                "widget": "number",
                "order": 2,
                "help_text": "Endurance, health, stamina, vitality",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Physical Attributes"
            },
            "intelligence": {
                "label": "Intelligence (INT)",
                "widget": "number",
                "order": 3,
                "help_text": "Reasoning, memory, learning ability",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Mental Attributes"
            },
            "wisdom": {
                "label": "Wisdom (WIS)",
                "widget": "number",
                "order": 4,
                "help_text": "Awareness, intuition, insight, perception",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Mental Attributes"
            },
            "charisma": {
                "label": "Charisma (CHA)",
                "widget": "number",
                "order": 5,
                "help_text": "Force of personality, leadership, persuasion",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Mental Attributes"
            }
        }

    @staticmethod
    def calculate_modifier(score: int) -> int:
        """
        Calculate ability modifier from score.

        Formula: (score - 10) // 2

        Args:
            score: Ability score (1-30)

        Returns:
            Ability modifier (-5 to +10 for scores 1-30)

        Examples:
            calculate_modifier(10) -> 0
            calculate_modifier(16) -> +3
            calculate_modifier(8) -> -1
        """
        return (score - 10) // 2

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """Validate attribute scores are within reasonable bounds."""
        for attr_name in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            score = data.get(attr_name)
            if score is not None and (score < 1 or score > 30):
                raise ValueError(f"{attr_name} must be between 1 and 30, got {score}")
        return True
