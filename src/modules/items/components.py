"""
Item components for the Items module.

Provides components for creating item entities:
- Item: Basic item properties (weight, value, rarity)
- Equippable: Marks entity as equippable (slot, requirements)
- Consumable: Marks entity as consumable (charges, effects)
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class ItemComponent(ComponentTypeDefinition):
    """
    Basic item component for physical objects.

    Stores common item properties like weight, value, rarity, and description.
    Items are entities that can be owned, carried, and potentially equipped.
    """

    type = "item"
    description = "Basic item properties"
    schema_version = "1.0.0"
    module = "items"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "weight": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Weight in pounds"
                },
                "value": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Value in gold pieces"
                },
                "rarity": {
                    "type": "string",
                    "description": "Item rarity"
                },
                "stackable": {
                    "type": "boolean",
                    "default": False,
                    "description": "Can multiple instances stack"
                },
                "quantity": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                    "description": "Number of items in stack"
                }
            },
            "required": ["weight", "value"]
        }

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """Validate rarity against registry if provided."""
        rarity = data.get('rarity')
        if rarity:
            registry = engine.create_registry('item_rarities', self.module)
            registry.validate(rarity, 'rarity')
        return True

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "weight": {
                "label": "Weight (lbs)",
                "widget": "number",
                "order": 0,
                "min": 0,
                "step": 0.1,
                "help_text": "Weight in pounds"
            },
            "value": {
                "label": "Value (gp)",
                "widget": "number",
                "order": 1,
                "min": 0,
                "step": 0.01,
                "help_text": "Value in gold pieces"
            },
            "rarity": {
                "label": "Rarity",
                "widget": "select",
                "order": 2,
                "registry": "item_rarities",
                "help_text": "Item rarity tier"
            },
            "stackable": {
                "label": "Stackable",
                "widget": "checkbox",
                "order": 3,
                "help_text": "Can multiple instances stack together"
            },
            "quantity": {
                "label": "Quantity",
                "widget": "number",
                "order": 4,
                "min": 1,
                "help_text": "Number of items in this stack"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Items don't appear directly on character sheets (they're entities)."""
        return {
            "visible": False,
            "category": "inventory",
            "priority": 100
        }


class EquippableComponent(ComponentTypeDefinition):
    """
    Equippable component marks an item entity as equippable.

    Defines which equipment slot the item occupies and any requirements
    for equipping it (e.g., minimum strength).
    """

    type = "equippable"
    description = "Marks item as equippable gear"
    schema_version = "1.0.0"
    module = "items"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "slot": {
                    "type": "string",
                    "description": "Equipment slot this item occupies"
                },
                "two_handed": {
                    "type": "boolean",
                    "default": False,
                    "description": "Requires both hands (occupies main_hand and off_hand)"
                },
                "required_strength": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Minimum strength to equip"
                },
                "required_level": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Minimum character level to equip"
                }
            },
            "required": ["slot"]
        }

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """Validate slot against equipment_slots registry."""
        slot = data.get('slot')
        if not slot:
            raise ValueError("slot is required for equippable items")

        # Validate against equipment_slots registry
        registry = engine.create_registry('equipment_slots', self.module)
        registry.validate(slot, 'slot')

        return True

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "slot": {
                "label": "Equipment Slot",
                "widget": "select",
                "order": 0,
                "registry": "equipment_slots",
                "help_text": "Which slot this item occupies when equipped"
            },
            "two_handed": {
                "label": "Two-Handed",
                "widget": "checkbox",
                "order": 1,
                "help_text": "Requires both hands to use"
            },
            "required_strength": {
                "label": "Required Strength",
                "widget": "number",
                "order": 2,
                "min": 0,
                "help_text": "Minimum strength score to equip"
            },
            "required_level": {
                "label": "Required Level",
                "widget": "number",
                "order": 3,
                "min": 1,
                "help_text": "Minimum character level to equip"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Equippable info doesn't appear directly on character sheets."""
        return {
            "visible": False,
            "category": "equipment",
            "priority": 100
        }


class ConsumableComponent(ComponentTypeDefinition):
    """
    Consumable component for items that can be used up.

    Examples: potions, scrolls, food, ammunition.
    Tracks charges/uses and describes the effect.
    """

    type = "consumable"
    description = "Consumable item with limited uses"
    schema_version = "1.0.0"
    module = "items"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "charges": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Remaining uses/charges"
                },
                "max_charges": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum charges when full"
                },
                "effect_description": {
                    "type": "string",
                    "description": "Description of what happens when consumed"
                },
                "rechargeable": {
                    "type": "boolean",
                    "default": False,
                    "description": "Can this item be recharged"
                }
            },
            "required": ["charges", "max_charges", "effect_description"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "charges": {
                "label": "Current Charges",
                "widget": "number",
                "order": 0,
                "min": 0,
                "help_text": "Remaining uses"
            },
            "max_charges": {
                "label": "Max Charges",
                "widget": "number",
                "order": 1,
                "min": 1,
                "help_text": "Maximum charges"
            },
            "effect_description": {
                "label": "Effect",
                "widget": "textarea",
                "order": 2,
                "help_text": "What happens when this item is used"
            },
            "rechargeable": {
                "label": "Rechargeable",
                "widget": "checkbox",
                "order": 3,
                "help_text": "Can this item be recharged"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Consumable info doesn't appear directly on character sheets."""
        return {
            "visible": False,
            "category": "inventory",
            "priority": 100
        }


__all__ = [
    'ItemComponent',
    'EquippableComponent',
    'ConsumableComponent'
]
