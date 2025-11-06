"""
Fantasy Combat Module for Arcane Arsenal.

Provides combat-related components for fantasy adventures including:
- Health: Hit points and damage tracking
- Armor: Protection and defense
- Weapon: Attack power and type
- Combat Stats: Strength, dexterity, constitution

This module demonstrates the dependency system by depending on core_components.
"""

from typing import List, Dict, Any
from ..base import Module, ComponentTypeDefinition


class HealthComponent(ComponentTypeDefinition):
    """
    Health component for tracking hit points.

    Tracks current HP, maximum HP, and temporary HP.
    """

    type = "health"
    description = "Tracks entity health and hit points"
    schema_version = "1.0.0"
    module = "fantasy_combat"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current_hp": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Current hit points"
                },
                "max_hp": {
                    "type": "number",
                    "minimum": 1,
                    "description": "Maximum hit points"
                },
                "temp_hp": {
                    "type": "number",
                    "minimum": 0,
                    "default": 0,
                    "description": "Temporary hit points"
                }
            },
            "required": ["current_hp", "max_hp"]
        }


class ArmorComponent(ComponentTypeDefinition):
    """
    Armor component for defense and protection.
    """

    type = "armor"
    description = "Armor class and damage resistance"
    schema_version = "1.0.0"
    module = "fantasy_combat"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "armor_class": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Armor class (AC)"
                },
                "armor_type": {
                    "type": "string",
                    "description": "Type of armor worn"
                }
            },
            "required": ["armor_class"]
        }


class WeaponComponent(ComponentTypeDefinition):
    """
    Weapon component for attacks.
    """

    type = "weapon"
    description = "Weapon attack properties"
    schema_version = "1.0.0"
    module = "fantasy_combat"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "damage_dice": {
                    "type": "string",
                    "description": "Damage dice (e.g., '1d8', '2d6')"
                },
                "damage_type": {
                    "type": "string",
                    "description": "Type of damage (slashing, piercing, bludgeoning, etc.)"
                },
                "attack_bonus": {
                    "type": "number",
                    "description": "Attack roll bonus"
                }
            },
            "required": ["damage_dice", "damage_type"]
        }


class FantasyCombatModule(Module):
    """
    Fantasy Combat module for Arcane Arsenal.

    Provides combat mechanics for fantasy tabletop RPGs including
    health tracking, armor, weapons, and combat stats.

    This module depends on core_components for entity positioning
    and basic identity.
    """

    @property
    def name(self) -> str:
        return "fantasy_combat"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "Fantasy Combat System"

    @property
    def description(self) -> str:
        return "Combat mechanics including health, armor, weapons, and damage for epic battles"

    def dependencies(self) -> List[str]:
        """Fantasy combat depends on core components for basic entity functionality."""
        return ['core_components']

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register Health, Armor, and Weapon components."""
        return [
            HealthComponent(),
            ArmorComponent(),
            WeaponComponent()
        ]


# Export
__all__ = [
    'FantasyCombatModule',
    'HealthComponent',
    'ArmorComponent',
    'WeaponComponent'
]
