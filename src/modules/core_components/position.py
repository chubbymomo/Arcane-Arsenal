"""
Position component - spatial location in the world.

Provides 3D coordinates and region information for positioning entities.
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class PositionComponent(ComponentTypeDefinition):
    """
    Spatial position in the world.

    Data schema:
        x (number, optional): X coordinate
        y (number, optional): Y coordinate
        z (number, optional): Z coordinate (defaults to 0 for 2D)
        region (string, optional): Named region or area

    Examples:
        {"x": 100, "y": 200, "z": 0, "region": "tavern"}
        {"x": 50.5, "y": 75.3, "region": "forest"}
        {"region": "inventory"}  # Abstract position
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
