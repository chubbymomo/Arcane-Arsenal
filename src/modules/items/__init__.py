"""
Items Module for Arcane Arsenal.

Provides item entities and equipment system for inventory management:

Components:
- Item: Basic item properties (weight, value, rarity)
- Equippable: Marks item as equippable gear (slot, requirements)
- Consumable: Marks item as consumable (charges, effects)

Relationships:
- owns: Entity owns an item
- equipped: Entity has an item equipped

System:
- EquipmentSystem: High-level API for equipping/unequipping items

Philosophy:
Items are ENTITIES, not components. A character has "owns" and "equipped"
relationships to item entities. This allows items to have their own components
and be first-class citizens in the ECS.
"""

from typing import List
from ..base import Module, ComponentTypeDefinition, RelationshipTypeDefinition
from .components import ItemComponent, EquippableComponent, ConsumableComponent
from .relationships import OwnsRelationship, EquippedRelationship
from .system import EquipmentSystem


class ItemsModule(Module):
    """
    Items module for entity-based inventory system.

    Provides components and relationships for managing items as entities.
    Items can be owned, equipped, consumed, and traded between entities.
    """

    def __init__(self):
        """Initialize items module."""
        self._equipment_system = None

    @property
    def name(self) -> str:
        return "items"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "Item & Equipment System"

    @property
    def description(self) -> str:
        return "Entity-based inventory with equipment slots, ownership, and item properties"

    def dependencies(self) -> List[str]:
        """Items depend on core_components for entity basics."""
        return ['core_components']

    def initialize(self, engine) -> None:
        """
        Initialize items module.

        Creates registries for equipment slots and item rarities.
        Initializes the EquipmentSystem for use by other systems.
        """
        # Create equipment slots registry
        slots = engine.create_registry('equipment_slots', self.name)
        slots.register('main_hand', 'Main hand weapon or tool', {'category': 'hands'})
        slots.register('off_hand', 'Off-hand weapon, shield, or tool', {'category': 'hands'})
        slots.register('head', 'Helmet, hat, or crown', {'category': 'armor'})
        slots.register('body', 'Armor, clothing, or robes', {'category': 'armor'})
        slots.register('hands', 'Gloves or gauntlets', {'category': 'armor'})
        slots.register('feet', 'Boots or shoes', {'category': 'armor'})
        slots.register('neck', 'Amulet or necklace', {'category': 'accessory'})
        slots.register('ring_1', 'First ring slot', {'category': 'accessory'})
        slots.register('ring_2', 'Second ring slot', {'category': 'accessory'})
        slots.register('back', 'Cloak or cape', {'category': 'accessory'})

        # Create item rarities registry
        rarities = engine.create_registry('item_rarities', self.name)
        rarities.register('common', 'Common item - readily available', {'color': 'gray'})
        rarities.register('uncommon', 'Uncommon item - harder to find', {'color': 'green'})
        rarities.register('rare', 'Rare item - valuable and powerful', {'color': 'blue'})
        rarities.register('very_rare', 'Very rare item - extremely valuable', {'color': 'purple'})
        rarities.register('legendary', 'Legendary item - one of a kind', {'color': 'orange'})
        rarities.register('artifact', 'Artifact - unique magical item', {'color': 'red'})

        # Initialize equipment system
        self._equipment_system = EquipmentSystem(engine)

    def get_equipment_system(self) -> EquipmentSystem:
        """
        Get the equipment system for this module.

        Returns:
            EquipmentSystem instance

        Raises:
            RuntimeError: If module has not been initialized
        """
        if self._equipment_system is None:
            raise RuntimeError("Items module not initialized. Call initialize() first.")
        return self._equipment_system

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register Item, Equippable, and Consumable components."""
        return [
            ItemComponent(),
            EquippableComponent(),
            ConsumableComponent()
        ]

    def register_relationship_types(self) -> List[RelationshipTypeDefinition]:
        """Register owns and equipped relationships."""
        return [
            OwnsRelationship(),
            EquippedRelationship()
        ]


__all__ = [
    'ItemsModule',
    'ItemComponent',
    'EquippableComponent',
    'ConsumableComponent',
    'OwnsRelationship',
    'EquippedRelationship',
    'EquipmentSystem'
]
