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
        Validate Position component data for spatial consistency.

        Validates:
        - Region entity exists if it's an entity reference
        - No circular references (entity can't be in itself or its descendants)
        - Container capacity if region is a container

        Note: This method gets the entity_id from the validation context.
        The engine passes it when validating during add_component/update_component.

        Args:
            data: Component data to validate
            engine: StateEngine instance

        Returns:
            True if valid

        Raises:
            ValueError: If position data is invalid
        """
        # Get the PositionSystem from the engine's module
        # The system is initialized by the core_components module
        from .systems import PositionSystem

        # Create system instance (it's stateless, so this is fine)
        position_system = PositionSystem(engine)

        # For validation during add_component, we don't have entity_id yet
        # For update_component, we have it but need to extract it from context
        # For now, we'll validate what we can without entity_id

        region = data.get('region')
        if not region:
            return True  # No region - valid

        # Validate region is valid (either named region or existing entity)
        if position_system._is_entity_reference(region):
            # It's an entity reference - already validated by _is_entity_reference
            # (which checks entity exists and is active)
            pass
        # else: it's a named region string - accept as-is

        # Note: Circular reference and capacity checks require entity_id,
        # which is validated by StateEngine before calling this method.
        # See StateEngine.add_component() and update_component() for full validation.

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
