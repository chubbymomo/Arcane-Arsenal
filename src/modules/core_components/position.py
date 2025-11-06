"""
Position component - spatial location in the world.

Provides 3D coordinates and region information for positioning entities.
Supports hierarchical positioning where entities can be positioned relative
to other entities (e.g., table in room, mug on table).
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class PositionComponent(ComponentTypeDefinition):
    """
    Spatial position in the world.

    Supports both absolute (world-level) and hierarchical (relative to parent entity)
    positioning. This allows for nested spatial relationships like objects in rooms,
    items on tables, etc.

    Data schema:
        x (number, optional): X coordinate
        y (number, optional): Y coordinate
        z (number, optional): Z coordinate (defaults to 0 for 2D)
        region (string, optional): Named region OR parent entity ID

    Region field usage:
        - Named area: "overworld", "dungeon_level_1", "tavern_main_room"
          → Position is absolute in that named area

        - Entity ID: "entity_abc123" (starts with "entity_")
          → Position is relative to parent entity's position
          → Use for hierarchical positioning (table in room, item on table)

    Examples:
        # Absolute position in world
        {"x": 100, "y": 200, "z": 0, "region": "overworld"}

        # Position relative to parent entity (table in tavern)
        {"x": 5, "y": 3, "z": 0, "region": "entity_tavern_id"}

        # Item on table (hierarchical)
        {"x": 0.5, "y": 0.5, "z": 1.2, "region": "entity_table_id"}

        # Abstract position (no coordinates)
        {"region": "inventory"}

    Hierarchical positioning:
        When region is an entity ID, x/y/z are offsets from the parent entity's
        world position. Calculate absolute world position by recursively adding
        parent positions. Use engine.get_world_position(entity_id) helper.

    Use cases:
        - World map rendering (calculate absolute positions)
        - Room layouts (furniture positioned in rooms)
        - Inventory systems (items in containers)
        - Nested spaces (drawers in desk in room in building)
    """

    type = "Position"
    description = "Spatial position in the world"
    schema_version = "1.0.0"
    module = "core_components"

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for Position component."""
        return {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
                "z": {"type": "number", "default": 0},
                "region": {"type": "string"}
            }
        }
