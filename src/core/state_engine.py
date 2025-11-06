"""
State Engine for Arcane Arsenal.

The StateEngine is the main API for managing world state. It coordinates
between storage, event bus, and validation to provide a clean interface
for all state operations.
"""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import json
import jsonschema

from .storage import WorldStorage
from .event_bus import EventBus
from .models import Entity, Component, Relationship, Event, now
from .result import Result
from .module_loader import ModuleLoader
from ..modules.core_components import CoreComponentsModule


class StateEngine:
    """
    Main API for world state management.

    Provides high-level operations for entities, components, and relationships
    with automatic validation and event emission.

    Attributes:
        world_path: Path to world directory
        storage: WorldStorage instance
        event_bus: EventBus instance
        component_validators: Dict of registered component type validators
        relationship_validators: Dict of registered relationship type validators
    """

    def __init__(self, world_path: str):
        """
        Initialize state engine for an existing world.

        Args:
            world_path: Path to world directory

        Raises:
            ValueError: If world doesn't exist
        """
        self.world_path = world_path
        db_path = os.path.join(world_path, 'world.db')

        if not os.path.exists(db_path):
            raise ValueError(f"World database not found at {db_path}. Use initialize_world() to create a new world.")

        # Initialize storage and event bus
        self.storage = WorldStorage(db_path)
        self.storage.initialize()
        self.event_bus = EventBus(self.storage)

        # Validators will be populated as modules register types
        self.component_validators: Dict[str, Any] = {}
        self.relationship_validators: Dict[str, Any] = {}

        # Load modules (core + any configured modules)
        self._load_modules()

    def _load_modules(self) -> None:
        """
        Load and register all modules.

        Uses ModuleLoader to discover and load modules based on world configuration.
        Strategy: 'config' if config.json exists, otherwise 'core_only' for safety.

        Registers all component types, relationship types, and event types to database.
        """
        # Create module loader
        loader = ModuleLoader(world_path=self.world_path)

        # Load modules (tries config first, falls back to core_only)
        modules = loader.load_modules(strategy='config')

        # Register all types from all modules
        for module in modules:
            # Register component types to database (safe for existing types due to INSERT OR REPLACE)
            for comp_type in module.register_component_types():
                self.storage.register_component_type(
                    comp_type.type,
                    comp_type.description,
                    comp_type.schema_version,
                    comp_type.module
                )
                self.component_validators[comp_type.type] = comp_type

            # Register relationship types to database
            for rel_type in module.register_relationship_types():
                self.storage.register_relationship_type(
                    rel_type.type,
                    rel_type.description,
                    rel_type.module
                )
                self.relationship_validators[rel_type.type] = rel_type

            # Register event types to database
            for event_type in module.register_event_types():
                self.storage.register_event_type(
                    event_type.type,
                    event_type.description,
                    event_type.module
                )

            # Call module's initialize hook
            try:
                module.initialize(self)
            except Exception as e:
                # Don't fail world loading if module initialization fails
                import logging
                logging.warning(f"Module '{module.name}' initialization failed: {e}")

    # ========== World Initialization ==========

    @staticmethod
    def initialize_world(world_path: str, world_name: str) -> 'StateEngine':
        """
        Create a new world and return initialized engine.

        This performs the complete world initialization sequence:
        1. Create world directory
        2. Create database with schema
        3. Create 'system' entity
        4. Register core event types
        5. Emit world.created event

        Args:
            world_path: Directory where world will be created
            world_name: Name of the world

        Returns:
            Initialized StateEngine instance

        Raises:
            ValueError: If world already exists
        """
        # Create world directory
        os.makedirs(world_path, exist_ok=True)
        db_path = os.path.join(world_path, 'world.db')

        if os.path.exists(db_path):
            raise ValueError(f"World already exists at {world_path}")

        # Initialize storage
        storage = WorldStorage(db_path)
        storage.initialize()

        # Register core event types
        storage.register_event_type('world.created', 'World was initialized', 'core')
        storage.register_event_type('entity.created', 'Entity was created', 'core')
        storage.register_event_type('entity.updated', 'Entity was updated', 'core')
        storage.register_event_type('entity.deleted', 'Entity was deleted', 'core')
        storage.register_event_type('entity.restored', 'Entity was restored', 'core')
        storage.register_event_type('component.added', 'Component was added to entity', 'core')
        storage.register_event_type('component.updated', 'Component was updated', 'core')
        storage.register_event_type('component.removed', 'Component was removed', 'core')
        storage.register_event_type('relationship.created', 'Relationship was created', 'core')
        storage.register_event_type('relationship.deleted', 'Relationship was deleted', 'core')

        # Create system entity
        system_entity = Entity.create('System', entity_id='system')
        storage.save_entity(system_entity)

        # Create default config.json (loads core_components only by default)
        config_path = os.path.join(world_path, 'config.json')
        default_config = {
            'world_name': world_name,
            'modules': ['core_components']  # Safe default - only core
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        # Log world creation event
        event_bus = EventBus(storage)
        event = Event.create(
            event_type='world.created',
            data={'world_name': world_name, 'world_path': world_path},
            actor_id='system'
        )
        event_bus.publish(event)

        # Create and return state engine
        # This will load modules from config.json via _load_modules()
        engine = StateEngine(world_path)

        return engine

    # ========== Entity Operations ==========

    def create_entity(self, name: str, actor_id: str = 'system') -> Result:
        """
        Create a new entity.

        Args:
            name: Entity name
            actor_id: Who is creating this entity

        Returns:
            Result with entity data or error
        """
        try:
            # Create entity
            entity = Entity.create(name)

            # Save to storage
            if not self.storage.save_entity(entity):
                return Result.fail("Failed to save entity", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='entity.created',
                data={'name': name, 'entity_id': entity.id},
                entity_id=entity.id,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok(entity.to_dict())

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Retrieve entity by ID.

        Args:
            entity_id: Entity ID to look up

        Returns:
            Entity if found, None otherwise
        """
        return self.storage.get_entity(entity_id)

    def list_entities(self, include_deleted: bool = False) -> List[Entity]:
        """
        List all entities.

        Args:
            include_deleted: Whether to include soft-deleted entities

        Returns:
            List of entities
        """
        return self.storage.list_entities(include_deleted)

    def update_entity(self, entity_id: str, name: str, actor_id: str = 'system') -> Result:
        """
        Update entity name.

        Args:
            entity_id: Entity to update
            name: New name
            actor_id: Who is updating this entity

        Returns:
            Result with updated entity data or error
        """
        try:
            # Check entity exists
            entity = self.storage.get_entity(entity_id)
            if not entity:
                return Result.fail(f"Entity {entity_id} not found", "ENTITY_NOT_FOUND")

            if not entity.is_active():
                return Result.fail(f"Entity {entity_id} is deleted", "ENTITY_DELETED")

            # Store old name for event
            old_name = entity.name

            # Update entity
            entity.name = name
            entity.modified_at = now()

            # Save to storage
            if not self.storage.save_entity(entity):
                return Result.fail("Failed to update entity", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='entity.updated',
                data={'entity_id': entity_id, 'old_name': old_name, 'new_name': name},
                entity_id=entity_id,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok(entity.to_dict())

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    def delete_entity(self, entity_id: str, actor_id: str = 'system') -> Result:
        """
        Soft-delete an entity.

        Args:
            entity_id: Entity to delete
            actor_id: Who is deleting this entity

        Returns:
            Result indicating success or error
        """
        try:
            # Check entity exists
            entity = self.storage.get_entity(entity_id)
            if not entity:
                return Result.fail(f"Entity {entity_id} not found", "ENTITY_NOT_FOUND")

            if not entity.is_active():
                return Result.fail(f"Entity {entity_id} is already deleted", "ENTITY_ALREADY_DELETED")

            # Delete entity
            if not self.storage.soft_delete_entity(entity_id, actor_id):
                return Result.fail("Failed to delete entity", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='entity.deleted',
                data={'entity_id': entity_id, 'name': entity.name},
                entity_id=entity_id,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok({'entity_id': entity_id})

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    def restore_entity(self, entity_id: str, actor_id: str = 'system') -> Result:
        """
        Restore a soft-deleted entity.

        Args:
            entity_id: Entity to restore
            actor_id: Who is restoring this entity

        Returns:
            Result indicating success or error
        """
        try:
            # Check entity exists
            entity = self.storage.get_entity(entity_id)
            if not entity:
                return Result.fail(f"Entity {entity_id} not found", "ENTITY_NOT_FOUND")

            if entity.is_active():
                return Result.fail(f"Entity {entity_id} is not deleted", "ENTITY_NOT_DELETED")

            # Restore entity
            if not self.storage.restore_entity(entity_id):
                return Result.fail("Failed to restore entity", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='entity.restored',
                data={'entity_id': entity_id, 'name': entity.name},
                entity_id=entity_id,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok({'entity_id': entity_id})

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    # ========== Component Operations ==========

    def add_component(self, entity_id: str, component_type: str, data: Dict[str, Any],
                     actor_id: str = 'system') -> Result:
        """
        Add a component to an entity.

        Args:
            entity_id: Entity to add component to
            component_type: Type of component
            data: Component data
            actor_id: Who is adding this component

        Returns:
            Result with component data or error
        """
        try:
            # Check entity exists
            entity = self.storage.get_entity(entity_id)
            if not entity:
                return Result.fail(f"Entity {entity_id} not found", "ENTITY_NOT_FOUND")

            if not entity.is_active():
                return Result.fail(f"Entity {entity_id} is deleted", "ENTITY_DELETED")

            # Check component type is registered
            registered_types = [t['type'] for t in self.storage.get_component_types()]
            if component_type not in registered_types:
                return Result.fail(
                    f"Component type {component_type} not registered",
                    "TYPE_NOT_REGISTERED"
                )

            # Check if entity already has this component type
            existing = self.storage.get_component(entity_id, component_type)
            if existing:
                return Result.fail(
                    f"Entity {entity_id} already has component {component_type}",
                    "COMPONENT_EXISTS"
                )

            # Validate data if validator exists
            if component_type in self.component_validators:
                validator = self.component_validators[component_type]
                try:
                    validator.validate(data)
                except jsonschema.ValidationError as e:
                    return Result.fail(
                        f"Component data validation failed: {e.message}",
                        "VALIDATION_ERROR"
                    )

            # Spatial validation for Position components
            if component_type == 'Position':
                validation_result = self._validate_position_data(entity_id, data)
                if not validation_result.success:
                    return validation_result

            # Create component
            component = Component.create(entity_id, component_type, data)

            # Save to storage
            if not self.storage.save_component(component):
                return Result.fail("Failed to save component", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='component.added',
                data={
                    'entity_id': entity_id,
                    'component_type': component_type,
                    'component_id': component.id,
                    'data': data
                },
                entity_id=entity_id,
                component_id=component.id,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok(component.to_dict())

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    def get_component(self, entity_id: str, component_type: str) -> Optional[Component]:
        """
        Get a specific component from an entity.

        Args:
            entity_id: Entity ID
            component_type: Type of component

        Returns:
            Component if found, None otherwise
        """
        return self.storage.get_component(entity_id, component_type)

    def get_entity_components(self, entity_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all components for an entity as {type: data}.

        Args:
            entity_id: Entity ID

        Returns:
            Dictionary mapping component types to their data
        """
        components = self.storage.get_entity_components(entity_id)
        return {c.component_type: c.data for c in components}

    def update_component(self, entity_id: str, component_type: str, data: Dict[str, Any],
                        actor_id: str = 'system') -> Result:
        """
        Update component data.

        Args:
            entity_id: Entity with the component
            component_type: Type of component to update
            data: New component data
            actor_id: Who is updating this component

        Returns:
            Result with updated component data or error
        """
        try:
            # Check entity exists
            entity = self.storage.get_entity(entity_id)
            if not entity:
                return Result.fail(f"Entity {entity_id} not found", "ENTITY_NOT_FOUND")

            if not entity.is_active():
                return Result.fail(f"Entity {entity_id} is deleted", "ENTITY_DELETED")

            # Check component exists
            component = self.storage.get_component(entity_id, component_type)
            if not component:
                return Result.fail(
                    f"Entity {entity_id} does not have component {component_type}",
                    "COMPONENT_NOT_FOUND"
                )

            # Validate data if validator exists
            if component_type in self.component_validators:
                validator = self.component_validators[component_type]
                try:
                    validator.validate(data)
                except jsonschema.ValidationError as e:
                    return Result.fail(
                        f"Component data validation failed: {e.message}",
                        "VALIDATION_ERROR"
                    )

            # Spatial validation for Position components
            if component_type == 'Position':
                validation_result = self._validate_position_data(entity_id, data)
                if not validation_result.success:
                    return validation_result

            # Store old data for event
            old_data = component.data.copy()

            # Update component
            component.data = data
            component.version += 1
            component.modified_at = now()

            # Save to storage
            if not self.storage.save_component(component):
                return Result.fail("Failed to update component", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='component.updated',
                data={
                    'entity_id': entity_id,
                    'component_type': component_type,
                    'component_id': component.id,
                    'old_data': old_data,
                    'new_data': data
                },
                entity_id=entity_id,
                component_id=component.id,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok(component.to_dict())

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    def remove_component(self, entity_id: str, component_type: str,
                        actor_id: str = 'system') -> Result:
        """
        Remove a component from an entity.

        Args:
            entity_id: Entity with the component
            component_type: Type of component to remove
            actor_id: Who is removing this component

        Returns:
            Result indicating success or error
        """
        try:
            # Check entity exists
            entity = self.storage.get_entity(entity_id)
            if not entity:
                return Result.fail(f"Entity {entity_id} not found", "ENTITY_NOT_FOUND")

            # Check component exists
            component = self.storage.get_component(entity_id, component_type)
            if not component:
                return Result.fail(
                    f"Entity {entity_id} does not have component {component_type}",
                    "COMPONENT_NOT_FOUND"
                )

            # Delete component
            if not self.storage.delete_component(component.id):
                return Result.fail("Failed to remove component", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='component.removed',
                data={
                    'entity_id': entity_id,
                    'component_type': component_type,
                    'component_id': component.id
                },
                entity_id=entity_id,
                component_id=component.id,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok({'component_id': component.id})

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    # ========== Relationship Operations ==========

    def create_relationship(self, from_id: str, to_id: str, rel_type: str,
                          metadata: Optional[Dict[str, Any]] = None,
                          actor_id: str = 'system') -> Result:
        """
        Create a relationship between entities.

        Args:
            from_id: Source entity ID
            to_id: Target entity ID
            rel_type: Type of relationship
            metadata: Optional metadata
            actor_id: Who is creating this relationship

        Returns:
            Result with relationship data or error
        """
        try:
            # Check both entities exist
            from_entity = self.storage.get_entity(from_id)
            if not from_entity:
                return Result.fail(f"Entity {from_id} not found", "ENTITY_NOT_FOUND")

            if not from_entity.is_active():
                return Result.fail(f"Entity {from_id} is deleted", "ENTITY_DELETED")

            to_entity = self.storage.get_entity(to_id)
            if not to_entity:
                return Result.fail(f"Entity {to_id} not found", "ENTITY_NOT_FOUND")

            if not to_entity.is_active():
                return Result.fail(f"Entity {to_id} is deleted", "ENTITY_DELETED")

            # Check relationship type is registered
            registered_types = [t['type'] for t in self.storage.get_relationship_types()]
            if rel_type not in registered_types:
                return Result.fail(
                    f"Relationship type {rel_type} not registered",
                    "TYPE_NOT_REGISTERED"
                )

            # Validate if validator exists
            if rel_type in self.relationship_validators:
                validator = self.relationship_validators[rel_type]
                if not validator.validate_from_entity(from_entity):
                    return Result.fail(
                        f"Entity {from_id} cannot be source of {rel_type} relationship",
                        "VALIDATION_ERROR"
                    )
                if not validator.validate_to_entity(to_entity):
                    return Result.fail(
                        f"Entity {to_id} cannot be target of {rel_type} relationship",
                        "VALIDATION_ERROR"
                    )

            # Create relationship
            relationship = Relationship.create(from_id, to_id, rel_type, metadata)

            # Save to storage
            if not self.storage.save_relationship(relationship):
                return Result.fail("Failed to save relationship", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='relationship.created',
                data={
                    'relationship_id': relationship.id,
                    'from_entity': from_id,
                    'to_entity': to_id,
                    'relationship_type': rel_type,
                    'metadata': metadata or {}
                },
                entity_id=from_id,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok(relationship.to_dict())

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    def get_relationships(self, entity_id: str, rel_type: Optional[str] = None,
                         direction: str = 'both') -> List[Relationship]:
        """
        Get relationships for an entity.

        Args:
            entity_id: Entity ID
            rel_type: Filter by relationship type (optional)
            direction: 'from', 'to', or 'both'

        Returns:
            List of relationships
        """
        relationships = self.storage.get_entity_relationships(entity_id, direction)

        if rel_type:
            relationships = [r for r in relationships if r.relationship_type == rel_type]

        return relationships

    def delete_relationship(self, relationship_id: str, actor_id: str = 'system') -> Result:
        """
        Delete a relationship.

        Args:
            relationship_id: Relationship ID to delete
            actor_id: Who is deleting this relationship

        Returns:
            Result indicating success or error
        """
        try:
            # Check relationship exists
            relationship = self.storage.get_relationship(relationship_id)
            if not relationship:
                return Result.fail(
                    f"Relationship {relationship_id} not found",
                    "RELATIONSHIP_NOT_FOUND"
                )

            if not relationship.is_active():
                return Result.fail(
                    f"Relationship {relationship_id} is already deleted",
                    "RELATIONSHIP_ALREADY_DELETED"
                )

            # Delete relationship
            if not self.storage.delete_relationship(relationship_id):
                return Result.fail("Failed to delete relationship", "STORAGE_ERROR")

            # Emit event
            event = Event.create(
                event_type='relationship.deleted',
                data={
                    'relationship_id': relationship_id,
                    'from_entity': relationship.from_entity,
                    'to_entity': relationship.to_entity,
                    'relationship_type': relationship.relationship_type
                },
                entity_id=relationship.from_entity,
                actor_id=actor_id
            )
            self.event_bus.publish(event)

            return Result.ok({'relationship_id': relationship_id})

        except Exception as e:
            return Result.fail(str(e), "UNEXPECTED_ERROR")

    # ========== Query Operations ==========

    def query_entities(self, component_types: Optional[List[str]] = None) -> List[Entity]:
        """
        Query entities by components.

        Args:
            component_types: List of component types that entities must have
                           If None, returns all entities

        Returns:
            List of entities matching the query
        """
        return self.storage.query_entities(component_types)

    def search_text(self, query: str) -> List[Entity]:
        """
        Full-text search across component data.

        Args:
            query: Search query string

        Returns:
            List of entities with components matching the search
        """
        return self.storage.search_text(query)

    # ========== Event Operations ==========

    def get_events(self, entity_id: Optional[str] = None,
                  event_type: Optional[str] = None,
                  limit: int = 100) -> List[Event]:
        """
        Retrieve event history.

        Args:
            entity_id: Filter by entity (optional)
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return

        Returns:
            List of events, most recent first
        """
        return self.storage.get_events(entity_id, event_type, limit)

    # ========== Type Registration ==========

    def register_component_type(self, definition: Any) -> Result:
        """
        Register a new component type.

        Args:
            definition: ComponentTypeDefinition instance

        Returns:
            Result indicating success or error
        """
        try:
            self.storage.register_component_type(
                definition.type,
                definition.description,
                definition.schema_version,
                definition.module
            )
            self.component_validators[definition.type] = definition
            return Result.ok({'type': definition.type})
        except Exception as e:
            return Result.fail(str(e), "REGISTRATION_ERROR")

    def register_relationship_type(self, definition: Any) -> Result:
        """
        Register a new relationship type.

        Args:
            definition: RelationshipTypeDefinition instance

        Returns:
            Result indicating success or error
        """
        try:
            self.storage.register_relationship_type(
                definition.type,
                definition.description,
                definition.module
            )
            self.relationship_validators[definition.type] = definition
            return Result.ok({'type': definition.type})
        except Exception as e:
            return Result.fail(str(e), "REGISTRATION_ERROR")

    # ========== Transaction Support ==========

    @contextmanager
    def transaction(self):
        """
        Context manager for transactions.

        Usage:
            with engine.transaction():
                engine.create_entity("Test")
                engine.add_component(...)
                # Auto-commits on success, rolls back on exception
        """
        self.storage.begin_transaction()
        try:
            yield
            self.storage.commit()
        except Exception:
            self.storage.rollback()
            raise

    # ========== Utility Methods ==========

    def get_world_position(self, entity_id: str) -> Optional[tuple]:
        """
        Calculate absolute world position for an entity.

        Handles hierarchical positioning by recursively adding parent positions.
        If an entity's Position.region is another entity ID, treats x/y/z as
        relative offsets from the parent entity's world position.

        Args:
            entity_id: Entity ID to get world position for

        Returns:
            Tuple of (x, y, z) in world coordinates, or None if entity has no Position

        Example:
            # Tavern at world position
            tavern: Position = {"x": 100, "y": 200, "z": 0, "region": "overworld"}

            # Table in tavern (relative position)
            table: Position = {"x": 5, "y": 3, "z": 0, "region": "entity_tavern_id"}

            engine.get_world_position(table_id)  # Returns (105, 203, 0)

        Note:
            - If region is not an entity ID, returns position as-is
            - Handles multiple levels of nesting (table → room → building → world)
            - Returns None if Position component missing at any level
            - Detects circular references (max depth 100)
        """
        MAX_DEPTH = 100  # Prevent infinite loops from circular references
        depth = 0

        current_id = entity_id
        total_x, total_y, total_z = 0.0, 0.0, 0.0

        while current_id and depth < MAX_DEPTH:
            # Get position component
            pos_component = self.get_component(current_id, 'Position')
            if not pos_component:
                # No position component
                return None

            pos_data = pos_component.data

            # Add this level's coordinates
            total_x += pos_data.get('x', 0)
            total_y += pos_data.get('y', 0)
            total_z += pos_data.get('z', 0)

            # Check if region is a parent entity
            region = pos_data.get('region', '')
            if region and region.startswith('entity_'):
                # Region is a parent entity ID - continue up the hierarchy
                current_id = region
                depth += 1
            else:
                # Region is a named area or empty - we're at the top level
                break

        if depth >= MAX_DEPTH:
            # Circular reference detected
            return None

        return (total_x, total_y, total_z)

    def get_entities_in_region(self, region: str, recursive: bool = False) -> List[Entity]:
        """
        Get all entities in a specific region.

        Args:
            region: Region name or entity ID to search for
            recursive: If True and region is an entity ID, include entities
                      in child regions (entities whose region is this entity's children)

        Returns:
            List of entities with Position.region matching the specified region

        Example:
            # Get all entities in the tavern
            entities = engine.get_entities_in_region('entity_tavern_id')

            # Get all entities in overworld
            entities = engine.get_entities_in_region('overworld')
        """
        # Get all entities with Position component
        positioned_entities = self.query_entities(['Position'])

        # Filter by region
        result = []
        for entity in positioned_entities:
            pos = self.get_component(entity.id, 'Position')
            if pos and pos.data.get('region') == region:
                result.append(entity)

        return result

    def _validate_position_data(self, entity_id: str, position_data: Dict[str, Any]) -> Result:
        """
        Validate Position component data for spatial consistency.

        Checks:
        - If region is an entity ID, that entity must exist
        - If region is an entity ID, that entity must have a Position component
        - No circular references (entity can't be positioned relative to itself or descendants)

        Args:
            entity_id: Entity that will have this position
            position_data: Position component data to validate

        Returns:
            Result indicating success or validation error
        """
        region = position_data.get('region', '')

        # If region is empty or a named area (not entity ID), it's valid
        if not region or not region.startswith('entity_'):
            return Result.ok({})

        parent_id = region

        # Check parent exists
        parent_entity = self.get_entity(parent_id)
        if not parent_entity:
            return Result.fail(
                f"Cannot position relative to entity '{parent_id}': entity does not exist",
                "INVALID_PARENT"
            )

        # Check parent is active
        if not parent_entity.is_active():
            return Result.fail(
                f"Cannot position relative to entity '{parent_id}': entity is deleted",
                "INVALID_PARENT"
            )

        # Check parent has Position component
        parent_position = self.get_component(parent_id, 'Position')
        if not parent_position:
            return Result.fail(
                f"Cannot position relative to entity '{parent_id}': parent has no Position component",
                "INVALID_PARENT"
            )

        # Check for circular references by simulating the hierarchy
        MAX_DEPTH = 100
        visited = {entity_id}  # Start with the entity being positioned
        current_id = parent_id
        depth = 0

        while current_id and depth < MAX_DEPTH:
            # If we've seen this entity before, it's a circular reference
            if current_id in visited:
                return Result.fail(
                    f"Cannot position relative to entity '{parent_id}': would create circular reference",
                    "CIRCULAR_REFERENCE"
                )

            visited.add(current_id)

            # Get this entity's position to check its parent
            pos = self.get_component(current_id, 'Position')
            if not pos:
                break  # Reached top level

            # Check if this entity's region is also an entity
            next_region = pos.data.get('region', '')
            if next_region and next_region.startswith('entity_'):
                current_id = next_region
                depth += 1
            else:
                break  # Reached top level

        return Result.ok({})

    def count_entities_in_region(self, region: str) -> int:
        """
        Count entities in a specific region.

        Args:
            region: Region name or entity ID

        Returns:
            Number of entities with Position.region matching the specified region
        """
        return len(self.get_entities_in_region(region))

    def can_add_to_region(self, region: str) -> Result:
        """
        Check if an entity can be added to a region.

        Validates:
        - Region exists (if it's an entity ID)
        - Container capacity (if region entity has Container component)

        Args:
            region: Region name or entity ID

        Returns:
            Result.ok() if can add, Result.fail() with reason if cannot
        """
        # If region is a named area (not entity ID), always allow
        if not region.startswith('entity_'):
            return Result.ok({})

        # Check region entity exists
        region_entity = self.get_entity(region)
        if not region_entity:
            return Result.fail(
                f"Region entity '{region}' does not exist",
                "REGION_NOT_FOUND"
            )

        if not region_entity.is_active():
            return Result.fail(
                f"Region entity '{region}' is deleted",
                "REGION_DELETED"
            )

        # Check Container component if it exists
        container = self.get_component(region, 'Container')
        if container:
            capacity = container.data.get('capacity')

            # If capacity is None/null, it's unlimited (bag of holding)
            if capacity is not None:
                current_count = self.count_entities_in_region(region)

                if current_count >= capacity:
                    return Result.fail(
                        f"Region '{region}' is at capacity ({capacity}/{capacity})",
                        "REGION_FULL"
                    )

        return Result.ok({'region': region})

    def close(self) -> None:
        """Close storage connection."""
        self.storage.close()
