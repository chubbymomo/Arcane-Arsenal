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

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """
        Validate region field against engine state.

        If region is an entity ID (starts with "entity_"), validates that
        the entity exists. Named regions (e.g., "overworld", "tavern") are
        accepted as-is.

        Args:
            data: Component data to validate
            engine: StateEngine instance for entity lookup

        Returns:
            True if valid

        Raises:
            ValueError: If region is an entity ID that doesn't exist
        """
        region = data.get('region')
        if not region:
            return True  # Region is optional

        # If region looks like an entity ID, validate it exists
        if region.startswith('entity_'):
            entity = engine.get_entity(region)
            if entity is None:
                raise ValueError(
                    f"Invalid region: entity '{region}' does not exist. "
                    f"Use a valid entity ID or a named region string."
                )

        # Named regions are accepted as-is (no registry needed)
        return True

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Return UI metadata for position fields."""
        return {
            "x": {
                "label": "X Coordinate",
                "widget": "number",
                "order": 0,
                "help_text": "Horizontal position"
            },
            "y": {
                "label": "Y Coordinate",
                "widget": "number",
                "order": 1,
                "help_text": "Vertical position"
            },
            "z": {
                "label": "Z Coordinate",
                "widget": "number",
                "order": 2,
                "help_text": "Elevation (defaults to 0)"
            },
            "region": {
                "label": "Region",
                "widget": "text",
                "order": 3,
                "help_text": "Named region or parent entity ID"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Position appears in the INFO category with low priority."""
        return {
            "visible": True,
            "category": "info",
            "priority": 20,
            "display_mode": "compact"
        }
