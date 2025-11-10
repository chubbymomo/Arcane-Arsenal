"""
Core Components Module for Arcane Arsenal.

Provides basic component and relationship types that are available in every world:
- Identity: Basic identification (description)
- Position: Spatial location (x, y, z, region)
- Container: Enables entities to hold other entities (capacity)
- PlayerCharacter: Marks entity as player-controlled character
- NPC: Marks entity as a non-player character with disposition
- Location: Marks entity as a location/place in the world
- located_at: Entity is physically at a location
- contains: Entity contains another entity

Also provides:
- PositionSystem: High-level API for spatial queries and validation
"""

from typing import List
from ..base import Module, ComponentTypeDefinition, RelationshipTypeDefinition, EventTypeDefinition
from .identity import IdentityComponent
from .position import PositionComponent
from .container import ContainerComponent
from .player_character import PlayerCharacterComponent
from .npc import NPCComponent
from .location import LocationComponent
from .systems import PositionSystem


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

    def __init__(self):
        """Initialize core components module."""
        self._position_system = None

    @property
    def name(self) -> str:
        return "core_components"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "Fundamental Arcane Components"

    @property
    def description(self) -> str:
        return "Essential components for positioning, identity, and containment. Required for all realms."

    @property
    def is_core(self) -> bool:
        return True

    def initialize(self, engine) -> None:
        """
        Initialize core_components module.

        Creates the character_sheet_categories registry that components can use
        to declare their display category on character sheets.
        """
        # Create character sheet categories registry
        categories = engine.create_registry('character_sheet_categories', self.name)
        categories.register('core', 'Core attributes and stats', {'order': 0})
        categories.register('combat', 'Combat abilities and stats', {'order': 1})
        categories.register('skills', 'Skills and proficiencies', {'order': 2})
        categories.register('resources', 'Expendable resources (spell slots, ki, etc.)', {'order': 3})
        categories.register('equipment', 'Equipped items and gear', {'order': 4})
        categories.register('inventory', 'Carried items and containers', {'order': 5})
        categories.register('spells', 'Spellcasting and magic', {'order': 6})
        categories.register('features', 'Class features and racial traits', {'order': 7})
        categories.register('info', 'Descriptive information', {'order': 8})
        categories.register('misc', 'Miscellaneous components', {'order': 9})

        # Initialize PositionSystem for spatial operations
        self._position_system = PositionSystem(engine)

    def get_position_system(self) -> PositionSystem:
        """
        Get the position system for this module.

        Returns:
            PositionSystem instance

        Raises:
            RuntimeError: If module has not been initialized
        """
        if self._position_system is None:
            raise RuntimeError("Core components module not initialized. Call initialize() first.")
        return self._position_system

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register Identity, Position, Container, PlayerCharacter, NPC, and Location components."""
        return [
            IdentityComponent(),
            PositionComponent(),
            ContainerComponent(),
            PlayerCharacterComponent(),
            NPCComponent(),
            LocationComponent()
        ]

    def register_relationship_types(self) -> List[RelationshipTypeDefinition]:
        """Register located_at and contains relationships."""
        return [
            LocatedAtRelationship(),
            ContainsRelationship()
        ]

    def register_blueprint(self) -> Optional[Any]:
        """
        Register Flask blueprint for core components API.

        Provides REST API endpoints for position queries:
        - GET /api/position/world/<entity_id> - Get world position
        - GET /api/position/nearby/<entity_id> - Get nearby entities
        """
        from .api import core_components_bp
        return core_components_bp


# Export everything for convenience
__all__ = [
    'CoreComponentsModule',
    'IdentityComponent',
    'PositionComponent',
    'ContainerComponent',
    'PlayerCharacterComponent',
    'NPCComponent',
    'LocationComponent',
    'LocatedAtRelationship',
    'ContainsRelationship',
    'PositionSystem'
]
