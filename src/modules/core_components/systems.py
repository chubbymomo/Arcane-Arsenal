"""
Systems for core_components module.

Provides high-level operations for spatial positioning and containment.
All operations use generic StateEngine methods - no special cases.
"""

from typing import List, Dict, Any, Optional, Tuple
from src.core.result import Result


class PositionSystem:
    """
    System for managing spatial positioning and hierarchical locations.

    This is a pure ECS system - it operates on Position and Container components
    using only generic StateEngine operations. No special-case logic in the engine.

    The Position component supports hierarchical positioning where entities can be
    positioned relative to other entities (e.g., room in building, item on table).

    Usage:
        system = PositionSystem(engine)
        world_pos = system.get_world_position(entity_id)
        entities_in_room = system.get_entities_in_region(room_id)
    """

    def __init__(self, engine):
        """
        Initialize position system.

        Args:
            engine: StateEngine instance
        """
        self.engine = engine

    def get_world_position(self, entity_id: str) -> Optional[Tuple[float, float, float]]:
        """
        Get the absolute world position of an entity.

        For entities positioned relative to other entities (hierarchical positioning),
        this recursively calculates the absolute world coordinates by traversing
        up the parent chain and summing all relative positions.

        Args:
            entity_id: Entity ID to get position for

        Returns:
            Tuple of (x, y, z) world coordinates, or None if entity has no Position

        Examples:
            # Absolute position
            position = {"x": 100, "y": 200, "z": 0, "region": "overworld"}
            get_world_position(entity_id) -> (100.0, 200.0, 0.0)

            # Hierarchical position
            # Building at (100, 200, 0) in overworld
            # Room at (10, 5, 0) in building
            # Table at (2, 3, 0) in room
            get_world_position(table_id) -> (112.0, 208.0, 0.0)
        """
        position = self.engine.get_component(entity_id, 'Position')
        if not position:
            return None

        # Get base coordinates (default to 0 if not specified)
        x = position.data.get('x', 0)
        y = position.data.get('y', 0)
        z = position.data.get('z', 0)

        # Check if positioned relative to another entity
        region = position.data.get('region')
        if region and self._is_entity_reference(region):
            # Recursively get parent's world position
            parent_pos = self.get_world_position(region)
            if parent_pos:
                # Add parent's position to our relative position
                x += parent_pos[0]
                y += parent_pos[1]
                z += parent_pos[2]

        return (float(x), float(y), float(z))

    def get_entities_in_region(self, region_id: str) -> List[str]:
        """
        Get all entities positioned in a specific region.

        A region can be either:
        - A named region string (e.g., "overworld", "dungeon_1")
        - An entity ID (for hierarchical positioning)

        Args:
            region_id: Region name or entity ID

        Returns:
            List of entity IDs positioned in this region

        Examples:
            # Get all entities in "overworld" region
            entities = system.get_entities_in_region("overworld")

            # Get all entities inside a container entity
            items_in_chest = system.get_entities_in_region(chest_id)
        """
        # Query all entities with Position component
        positioned_entities = self.engine.query_entities(['Position'])

        entities_in_region = []
        for entity_id in positioned_entities:
            position = self.engine.get_component(entity_id, 'Position')
            if position and position.data.get('region') == region_id:
                entities_in_region.append(entity_id)

        return entities_in_region

    def count_entities_in_region(self, region_id: str) -> int:
        """
        Count entities in a region.

        More efficient than getting all entities and counting them.

        Args:
            region_id: Region name or entity ID

        Returns:
            Number of entities in the region
        """
        return len(self.get_entities_in_region(region_id))

    def can_add_to_region(self, region_id: str) -> Result:
        """
        Check if an entity can be added to a region.

        For regions that are container entities, checks capacity constraints.
        For named regions, always returns success.

        Args:
            region_id: Region name or entity ID

        Returns:
            Result indicating if addition is allowed

        Examples:
            # Check if we can add item to a chest
            result = system.can_add_to_region(chest_id)
            if result.success:
                # Add the item
                engine.update_component(item_id, 'Position', {'region': chest_id})
        """
        # If region is not an entity, allow addition
        if not self._is_entity_reference(region_id):
            return Result.ok({'can_add': True, 'reason': 'Named region has no capacity limit'})

        # Get container component if region is an entity
        container = self.engine.get_component(region_id, 'Container')
        if not container:
            # Entity exists but is not a container - allow addition
            return Result.ok({'can_add': True, 'reason': 'Entity is not a container'})

        # Check capacity
        capacity = container.data.get('capacity')
        if capacity is None:
            # Unlimited capacity
            return Result.ok({'can_add': True, 'reason': 'Unlimited capacity'})

        # Count current entities in region
        current_count = self.count_entities_in_region(region_id)

        if current_count >= capacity:
            return Result.fail(
                f"Container is at capacity ({current_count}/{capacity})",
                "CONTAINER_FULL"
            )

        return Result.ok({
            'can_add': True,
            'current_count': current_count,
            'capacity': capacity,
            'remaining': capacity - current_count
        })

    def validate_position_data(self, entity_id: str, position_data: Dict[str, Any]) -> Result:
        """
        Validate Position component data for spatial consistency.

        Checks:
        - Region entity exists if it's an entity reference
        - No circular references (entity can't be in itself or its descendants)
        - Container capacity if region is a container

        Args:
            entity_id: Entity that will have this position
            position_data: Position component data to validate

        Returns:
            Result indicating if position data is valid

        Note:
            This is called by PositionComponent.validate_with_engine()
        """
        region = position_data.get('region')
        if not region:
            # No region specified - valid
            return Result.ok({'valid': True})

        # If region is an entity reference, validate it
        if self._is_entity_reference(region):
            # Check that region entity exists
            region_entity = self.engine.get_entity(region)
            if not region_entity or not region_entity.is_active():
                return Result.fail(
                    f"Region entity '{region}' does not exist or is deleted",
                    "INVALID_REGION"
                )

            # Check for circular references
            if self._creates_circular_reference(entity_id, region):
                return Result.fail(
                    f"Cannot position entity in '{region}': would create circular reference",
                    "CIRCULAR_REFERENCE"
                )

            # Check container capacity
            capacity_result = self.can_add_to_region(region)
            if not capacity_result.success:
                # Get current position to see if entity is already in this region
                current_position = self.engine.get_component(entity_id, 'Position')
                if current_position and current_position.data.get('region') == region:
                    # Entity is already in this region - allow update
                    return Result.ok({'valid': True, 'note': 'Entity already in region'})
                else:
                    # Container is full and entity is not already there
                    return capacity_result

        # Named region or all checks passed
        return Result.ok({'valid': True})

    def _is_entity_reference(self, value: str) -> bool:
        """
        Check if a value is an entity reference.

        Args:
            value: String to check

        Returns:
            True if value is a valid entity ID
        """
        entity = self.engine.get_entity(value)
        return entity is not None and entity.is_active()

    def _creates_circular_reference(self, entity_id: str, new_region: str) -> bool:
        """
        Check if setting an entity's region would create a circular reference.

        A circular reference occurs when:
        - Entity A is in Entity B
        - Entity B is in Entity A

        Or any longer chain:
        - Entity A is in Entity B
        - Entity B is in Entity C
        - Entity C is in Entity A

        Args:
            entity_id: Entity being positioned
            new_region: Proposed region (entity ID)

        Returns:
            True if this would create a circular reference
        """
        if entity_id == new_region:
            # Entity can't be in itself
            return True

        # Traverse up the parent chain from new_region
        current_region = new_region
        visited = set()

        while current_region and self._is_entity_reference(current_region):
            if current_region in visited:
                # Detected a cycle (not involving entity_id)
                return False

            if current_region == entity_id:
                # Found entity_id in the parent chain - circular reference!
                return True

            visited.add(current_region)

            # Move up to parent region
            position = self.engine.get_component(current_region, 'Position')
            if position:
                current_region = position.data.get('region')
            else:
                break

        return False


__all__ = ['PositionSystem']
