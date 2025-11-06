"""
Container Component.

The Container component allows entities to hold other entities with optional capacity limits.

Usage:
    - Unlimited container (bag of holding):
      {"capacity": null}

    - Limited container (chest with 10 slots):
      {"capacity": 10}

Entity Type by Components:
    - Has Container: Can hold items
    - No Container: Cannot hold items (no capacity enforcement)

Examples:
    # Bag of Holding (unlimited)
    engine.add_component(bag_id, 'Container', {'capacity': None})

    # Chest (10 item limit)
    engine.add_component(chest_id, 'Container', {'capacity': 10})

    # Check before adding
    result = engine.can_add_to_region(chest_id)
    if result.success:
        engine.add_component(item_id, 'Position', {'region': chest_id, 'x': 0, 'y': 0, 'z': 0})

Querying:
    # Get all containers
    containers = engine.query_entities(['Container'])

    # Count items in container
    count = engine.count_entities_in_region(chest_id)

    # Check capacity
    result = engine.can_add_to_region(chest_id)
"""

from typing import Dict, Any
from ...core.models import Entity


class ContainerComponentType:
    """Container component definition."""

    type = 'Container'
    description = 'Enables an entity to contain other entities with optional capacity limits'
    schema_version = '1.0.0'
    module = 'core'

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """
        Get JSON schema for Container component.

        Schema:
            capacity: Optional integer for item limit (null = unlimited)
        """
        return {
            "type": "object",
            "properties": {
                "capacity": {
                    "oneOf": [
                        {"type": "integer", "minimum": 0},
                        {"type": "null"}
                    ],
                    "description": "Maximum number of entities this container can hold (null = unlimited)"
                }
            },
            "required": ["capacity"],
            "additionalProperties": False
        }

    @staticmethod
    def validate(data: Dict[str, Any]) -> None:
        """
        Validate container data against schema.

        Args:
            data: Component data to validate

        Raises:
            jsonschema.ValidationError: If data doesn't match schema
        """
        import jsonschema
        schema = ContainerComponentType.get_schema()
        jsonschema.validate(data, schema)

    @staticmethod
    def validate_entity(entity: Entity) -> bool:
        """
        Validate if entity can have Container component.

        Any entity can be a container - no restrictions.

        Args:
            entity: Entity to validate

        Returns:
            Always True
        """
        return True
