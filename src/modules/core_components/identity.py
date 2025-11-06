"""
Identity component - basic identification for any entity.

Provides a description for any entity. Entity type is determined by which
components it has, not by tags (to prevent AI hallucination through inconsistent
categorization).
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class IdentityComponent(ComponentTypeDefinition):
    """
    Basic identity information for any entity.

    Data schema:
        description (string, required): Text description of the entity

    Examples:
        {"description": "A brave warrior"}
        {"description": "An old wooden tavern"}
        {"description": "A rusty sword"}

    Note:
        Entity type is determined by component composition, not tags.
        - Characters have: Identity + Position + CharacterStats (Phase 2)
        - Locations have: Identity + Position + LocationProperties (Phase 2)
        - Items have: Identity + ItemProperties (Phase 2)

        Use engine.query_entities(['ComponentType']) to find entities by type.
    """

    type = "Identity"
    description = "Basic identity information for any entity"
    schema_version = "1.0.0"
    module = "core_components"

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for Identity component."""
        return {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "minLength": 1
                }
            },
            "required": ["description"],
            "additionalProperties": False
        }
