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

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "current_hp": {
                "label": "Current HP",
                "widget": "number",
                "order": 0,
                "min": 0,
                "help_text": "Current hit points"
            },
            "max_hp": {
                "label": "Max HP",
                "widget": "number",
                "order": 1,
                "min": 1,
                "help_text": "Maximum hit points"
            },
            "temp_hp": {
                "label": "Temporary HP",
                "widget": "number",
                "order": 2,
                "min": 0,
                "help_text": "Temporary hit points (lost first)"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        return {
            "visible": True,
            "category": "core",
            "priority": 5,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None) -> str:
        """Custom renderer with progress bar for HP."""
        from markupsafe import escape

        current = data.get('current_hp', 0)
        maximum = data.get('max_hp', 1)
        temp = data.get('temp_hp', 0)

        # Calculate percentage for progress bar
        percent = int((current / maximum) * 100) if maximum > 0 else 0

        # Color based on HP percentage
        if percent > 50:
            color_class = "bg-success"
        elif percent > 25:
            color_class = "bg-warning"
        else:
            color_class = "bg-danger"

        html = f'''
        <div class="health-component">
            <div class="health-label">
                <strong>Hit Points:</strong> {escape(str(current))}/{escape(str(maximum))}
                {f' (+{escape(str(temp))} temp)' if temp > 0 else ''}
            </div>
            <div class="progress" style="height: 20px;">
                <div class="progress-bar {color_class}" role="progressbar"
                     style="width: {percent}%"
                     aria-valuenow="{current}" aria-valuemin="0" aria-valuemax="{maximum}">
                    {percent}%
                </div>
            </div>
        </div>
        '''
        return html


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

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "armor_class": {
                "label": "Armor Class (AC)",
                "widget": "number",
                "order": 0,
                "min": 0,
                "help_text": "Total armor class"
            },
            "armor_type": {
                "label": "Armor Type",
                "widget": "select",
                "order": 1,
                "registry": "armor_types",
                "help_text": "Type of armor worn"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        return {
            "visible": True,
            "category": "combat",
            "priority": 10,
            "display_mode": "compact"
        }

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """
        Validate armor_type against registered armor types.

        Args:
            data: Component data to validate
            engine: StateEngine instance for querying registered types

        Returns:
            True if valid

        Raises:
            ValueError: If armor_type is not in registered armor_types registry
        """
        armor_type = data.get('armor_type')
        if not armor_type:
            # armor_type is optional, so if not provided, validation passes
            return True

        # Get armor_types registry
        armor_registry = engine.create_registry('armor_types', self.module)

        # Validate against registry
        try:
            armor_registry.validate(armor_type, 'armor_type')
        except ValueError as e:
            raise ValueError(
                f"Invalid armor_type '{armor_type}'. "
                f"Valid types: {', '.join(armor_registry.get_keys())}"
            )

        return True


class WeaponComponent(ComponentTypeDefinition):
    """
    Weapon component for attacks.

    Validates damage_dice using RNG module's DiceParser and damage_type
    against the fantasy_combat module's damage_types registry.
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

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "damage_dice": {
                "label": "Damage Dice",
                "widget": "text",
                "order": 0,
                "placeholder": "1d8+3",
                "help_text": "Dice notation for damage (e.g., 1d8, 2d6+2)"
            },
            "damage_type": {
                "label": "Damage Type",
                "widget": "select",
                "order": 1,
                "registry": "damage_types",
                "help_text": "Type of damage dealt"
            },
            "attack_bonus": {
                "label": "Attack Bonus",
                "widget": "number",
                "order": 2,
                "help_text": "Bonus to attack rolls"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        return {
            "visible": True,
            "category": "combat",
            "priority": 20,
            "display_mode": "full"
        }

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """
        Validate damage_dice and damage_type fields.

        Args:
            data: Component data to validate
            engine: StateEngine instance for querying registered types

        Returns:
            True if valid

        Raises:
            ValueError: If damage_dice is not valid dice notation or
                       damage_type is not in registered damage_types registry
        """
        # Validate damage_dice (required)
        damage_dice = data.get('damage_dice')
        if not damage_dice:
            raise ValueError("damage_dice is required")

        # Validate dice notation format using the RNG module's parser
        try:
            from src.modules.rng.dice_parser import DiceParser
            parser = DiceParser()
            parser.parse(damage_dice)  # Will raise ValueError if invalid
        except ValueError as e:
            raise ValueError(
                f"Invalid damage_dice notation '{damage_dice}': {str(e)}. "
                f"Use standard dice notation like '1d8', '2d6+3', or '1d10+1d4'."
            )

        # Validate damage_type (required)
        damage_type = data.get('damage_type')
        if not damage_type:
            raise ValueError("damage_type is required")

        # Get damage_types registry
        damage_registry = engine.create_registry('damage_types', self.module)

        # Validate against registry
        try:
            damage_registry.validate(damage_type, 'damage_type')
        except ValueError as e:
            raise ValueError(
                f"Invalid damage_type '{damage_type}'. "
                f"Valid types: {', '.join(damage_registry.get_keys())}"
            )

        return True


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
        """
        Fantasy combat depends on core components and RNG module.

        - core_components: Basic entity functionality (Position, Identity)
        - rng: DiceParser for damage_dice validation
        """
        return ['core_components', 'rng']

    def initialize(self, engine) -> None:
        """
        Initialize fantasy_combat module registries.

        Creates and populates armor_types and damage_types registries
        with common fantasy RPG values.
        """
        # Create armor types registry
        armor_types = engine.create_registry('armor_types', self.name)
        armor_types.register('light', 'Light armor - cloth, leather', {'weight': 'light'})
        armor_types.register('medium', 'Medium armor - chainmail, hide', {'weight': 'medium'})
        armor_types.register('heavy', 'Heavy armor - plate, scale', {'weight': 'heavy'})
        armor_types.register('shield', 'Shield - adds to AC', {'weight': 'varies'})

        # Create damage types registry
        damage_types = engine.create_registry('damage_types', self.name)

        # Physical damage types
        damage_types.register('slashing', 'Slashing damage - swords, axes', {'category': 'physical'})
        damage_types.register('piercing', 'Piercing damage - arrows, spears', {'category': 'physical'})
        damage_types.register('bludgeoning', 'Bludgeoning damage - clubs, hammers', {'category': 'physical'})

        # Elemental damage types
        damage_types.register('fire', 'Fire damage - flames, heat', {'category': 'elemental'})
        damage_types.register('cold', 'Cold damage - ice, frost', {'category': 'elemental'})
        damage_types.register('lightning', 'Lightning damage - electricity', {'category': 'elemental'})
        damage_types.register('thunder', 'Thunder damage - sonic force', {'category': 'elemental'})

        # Magical damage types
        damage_types.register('acid', 'Acid damage - corrosive', {'category': 'magical'})
        damage_types.register('poison', 'Poison damage - toxins', {'category': 'magical'})
        damage_types.register('necrotic', 'Necrotic damage - death energy', {'category': 'magical'})
        damage_types.register('radiant', 'Radiant damage - holy light', {'category': 'magical'})
        damage_types.register('force', 'Force damage - pure magical energy', {'category': 'magical'})
        damage_types.register('psychic', 'Psychic damage - mental energy', {'category': 'magical'})

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
