"""
Identity component - basic identification for any entity.

Provides a description and tags for categorizing entities.
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class IdentityComponent(ComponentTypeDefinition):
    """
    Basic identity information for any entity.

    Data schema:
        description (string, required): Text description of the entity
        tags (array of strings, optional): Categorization tags

    Examples:
        {"description": "A brave warrior", "tags": ["player", "human"]}
        {"description": "An old wooden tavern", "tags": ["building", "location"]}
        {"description": "A rusty sword", "tags": ["weapon", "item"]}
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
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": []
                }
            },
            "required": ["description"]
        }
