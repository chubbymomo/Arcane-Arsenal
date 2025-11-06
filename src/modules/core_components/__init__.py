"""
Core Components Module for Arcane Arsenal.

Provides basic component and relationship types that are available in every world:
- Identity: Basic identification (description)
- Position: Spatial location (x, y, z, region)
- Container: Enables entities to hold other entities (capacity)
- PlayerCharacter: Marks entity as player-controlled character
- located_at: Entity is physically at a location
- contains: Entity contains another entity
"""

from typing import List
from ..base import Module, ComponentTypeDefinition, RelationshipTypeDefinition, EventTypeDefinition
from .identity import IdentityComponent
from .position import PositionComponent
from .container import ContainerComponentType
from .player_character import PlayerCharacterComponent


class LocatedAtRelationship(RelationshipTypeDefinition):
    """
    Relationship indicating an entity is physically at a location.

    From entity: Any entity that can be positioned
    To entity: Any entity that represents a location

    Examples:
        Character -> Tavern
        Item -> Chest
        NPC -> Forest
    """

    type = "located_at"
    description = "Entity is physically at a location"
    module = "core_components"


class ContainsRelationship(RelationshipTypeDefinition):
    """
    Relationship indicating an entity contains another entity.

    From entity: Container (chest, room, inventory, etc.)
    To entity: Contained entity (item, character, etc.)

    Examples:
        Chest -> Gold Coins
        Room -> Furniture
        Character -> Quest Item
    """

    type = "contains"
    description = "Entity contains another entity"
    module = "core_components"


class CoreComponentsModule(Module):
    """
    Core components module.

    Provides fundamental component types and relationships that ship
    with Arcane Arsenal. This module is automatically loaded when
    initializing a world.
    """

    @property
    def name(self) -> str:
        return "core_components"

    @property
    def version(self) -> str:
        return "1.0.0"

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register Identity, Position, Container, and PlayerCharacter components."""
        return [
            IdentityComponent(),
            PositionComponent(),
            ContainerComponentType(),
            PlayerCharacterComponent()
        ]

    def register_relationship_types(self) -> List[RelationshipTypeDefinition]:
        """Register located_at and contains relationships."""
        return [
            LocatedAtRelationship(),
            ContainsRelationship()
        ]


# Export everything for convenience
__all__ = [
    'CoreComponentsModule',
    'IdentityComponent',
    'PositionComponent',
    'ContainerComponentType',
    'PlayerCharacterComponent',
    'LocatedAtRelationship',
    'ContainsRelationship'
]
