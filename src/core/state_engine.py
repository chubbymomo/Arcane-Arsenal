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
from .result import Result, ErrorCode
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

        # Cache for ModuleRegistry instances (ensures singleton per registry)
        # This prevents cache synchronization issues when multiple callers
        # request the same registry - they all get the same instance
        self._registry_instances: Dict[str, 'ModuleRegistry'] = {}

        # Modules storage (for cross-module access)
        self._modules: Dict[str, Any] = {}

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

        # Store modules for cross-module access
        for module in modules:
            self._modules[module.name] = module

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

            # Register roll types to database
            for roll_type in module.register_roll_types():
                self.storage.register_roll_type(
                    roll_type.type,
                    roll_type.description,
                    roll_type.module,
                    roll_type.category
                )

            # Call module's initialize hook
            try:
                module.initialize(self)
            except Exception as e:
                # Don't fail world loading if module initialization fails
                import logging
                logging.warning(f"Module '{module.name}' initialization failed: {e}")

    def get_module(self, module_name: str) -> Optional[Any]:
        """
        Get a loaded module by name.

        Enables cross-module access to module-specific functionality.
        For example, AIContextBuilder can access items module's EquipmentSystem.

        Args:
            module_name: Name of the module (e.g., 'items', 'core_components')

        Returns:
            Module instance or None if not loaded

        Example:
            items_module = engine.get_module('items')
            equipment_system = items_module.get_equipment_system()
        """
        return self._modules.get(module_name)

    # ========== World Initialization ==========

    @staticmethod
    def initialize_world(world_path: str, world_name: str, modules: List[str] = None) -> 'StateEngine':
        """
        Create a new world and return initialized engine.

        This performs the complete world initialization sequence:
        1. Create world directory
        2. Create database with schema
        3. Create 'system' entity
        4. Register core event types
        5. Create config.json with specified modules
        6. Emit world.created event

        Args:
            world_path: Directory where world will be created
            world_name: Name of the world
            modules: List of module names to enable (default: ['core_components'])

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

        # Create config.json with specified modules
        config_path = os.path.join(world_path, 'config.json')
        if modules is None:
            modules = ['core_components']  # Safe default - only core

        # Ensure core_components is always included
        if 'core_components' not in modules:
            modules = ['core_components'] + modules

        config = {
            'world_name': world_name,
            'modules': modules
        }
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Log world creation event
        event_bus = EventBus(storage)
        event = Event.create(
            event_type='world.created',
            data={
                'world_name': world_name,
                'world_path': world_path,
                'modules': modules
            },
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
                return Result.fail("Failed to save entity", ErrorCode.STORAGE_ERROR)

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
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

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
                return Result.fail("Failed to update entity", ErrorCode.STORAGE_ERROR)

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
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

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
                return Result.fail("Failed to delete entity", ErrorCode.STORAGE_ERROR)

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
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

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
                return Result.fail("Failed to restore entity", ErrorCode.STORAGE_ERROR)

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
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

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

        IMPORTANT: Always check result.success! Ignoring failures causes silent bugs.
        """
        try:
            # Check entity exists
            entity = self.storage.get_entity(entity_id)
            if not entity:
                error_msg = f"Entity {entity_id} not found"
                logger.error(f"❌ add_component FAILED: {error_msg}")
                return Result.fail(error_msg, "ENTITY_NOT_FOUND")

            if not entity.is_active():
                error_msg = f"Entity {entity_id} is deleted"
                logger.error(f"❌ add_component FAILED: {error_msg}")
                return Result.fail(error_msg, "ENTITY_DELETED")

            # Check component type is registered
            registered_types = [t['type'] for t in self.storage.get_component_types()]
            if component_type not in registered_types:
                error_msg = f"Component type {component_type} not registered"
                logger.error(f"❌ add_component FAILED: {error_msg}")
                return Result.fail(error_msg, "TYPE_NOT_REGISTERED")

            # Check if entity already has this component type
            existing = self.storage.get_component(entity_id, component_type)
            if existing:
                error_msg = f"Entity {entity_id} already has component {component_type}"
                logger.error(f"❌ add_component FAILED: {error_msg}")
                return Result.fail(error_msg, "COMPONENT_EXISTS")

            # Validate data if validator exists
            if component_type in self.component_validators:
                validator = self.component_validators[component_type]
                try:
                    validator.validate(data)
                except jsonschema.ValidationError as e:
                    error_msg = f"Component data validation failed: {e.message}"
                    logger.error(f"❌ add_component FAILED ({component_type} on {entity_id}): {error_msg}")
                    logger.error(f"   Data: {data}")
                    return Result.fail(error_msg, "VALIDATION_ERROR")

                # Additional validation against engine state
                try:
                    validator.validate_with_engine(data, self)
                except ValueError as e:
                    error_msg = f"Component data validation failed: {str(e)}"
                    logger.error(f"❌ add_component FAILED ({component_type} on {entity_id}): {error_msg}")
                    logger.error(f"   Data: {data}")
                    return Result.fail(error_msg, "VALIDATION_ERROR")

            # Spatial validation for Position components
            if component_type == 'Position':
                validation_result = self._validate_position_with_system(entity_id, data)
                if not validation_result.success:
                    logger.error(f"❌ add_component FAILED (Position on {entity_id}): {validation_result.error}")
                    logger.error(f"   Data: {data}")
                    return validation_result

            # Create component
            component = Component.create(entity_id, component_type, data)

            # Save to storage
            if not self.storage.save_component(component):
                error_msg = "Failed to save component"
                logger.error(f"❌ add_component FAILED ({component_type} on {entity_id}): {error_msg}")
                return Result.fail(error_msg, ErrorCode.STORAGE_ERROR)

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
            error_msg = str(e)
            logger.error(f"❌ add_component FAILED ({component_type} on {entity_id}): {error_msg}", exc_info=True)
            return Result.fail(error_msg, ErrorCode.UNEXPECTED_ERROR)

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

                # Additional validation against engine state
                try:
                    validator.validate_with_engine(data, self)
                except ValueError as e:
                    return Result.fail(
                        f"Component data validation failed: {str(e)}",
                        "VALIDATION_ERROR"
                    )

            # Spatial validation for Position components
            if component_type == 'Position':
                validation_result = self._validate_position_with_system(entity_id, data)
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
                return Result.fail("Failed to update component", ErrorCode.STORAGE_ERROR)

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
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

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
                return Result.fail("Failed to remove component", ErrorCode.STORAGE_ERROR)

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
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

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
                return Result.fail("Failed to save relationship", ErrorCode.STORAGE_ERROR)

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
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """
        Get a relationship by ID.

        Args:
            relationship_id: Relationship ID

        Returns:
            Relationship if found, None otherwise
        """
        return self.storage.get_relationship(relationship_id)

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
                return Result.fail("Failed to delete relationship", ErrorCode.STORAGE_ERROR)

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
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

    def delete_relationship_by_entities(self, from_id: str, to_id: str, rel_type: str,
                                       actor_id: str = 'system') -> Result:
        """
        Delete a relationship between two entities by finding and removing it.

        This is a convenience method that mirrors create_relationship() - while
        create_relationship takes entity IDs and type, this allows deletion
        using the same parameters without requiring the caller to find the
        relationship ID first.

        Args:
            from_id: Source entity ID
            to_id: Target entity ID
            rel_type: Type of relationship to delete
            actor_id: Who is deleting this relationship

        Returns:
            Result indicating success or error
        """
        try:
            # Get all relationships of this type from the from_entity
            relationships = self.get_relationships(from_id, rel_type=rel_type, direction='from')

            # Find the specific relationship to the to_entity
            target_relationship = None
            for rel in relationships:
                if rel.to_entity == to_id:
                    target_relationship = rel
                    break

            if not target_relationship:
                return Result.fail(
                    f"No {rel_type} relationship found from {from_id} to {to_id}",
                    "RELATIONSHIP_NOT_FOUND"
                )

            # Delete the relationship using the existing method
            return self.delete_relationship(target_relationship.id, actor_id=actor_id)

        except Exception as e:
            return Result.fail(str(e), ErrorCode.UNEXPECTED_ERROR)

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

    def get_component_types(self) -> List[Dict[str, Any]]:
        """
        Get all registered component types.

        Returns:
            List of component type definitions with type, description, schema_version, module
        """
        return self.storage.get_component_types()

    def get_relationship_types(self) -> List[Dict[str, Any]]:
        """
        Get all registered relationship types.

        Returns:
            List of relationship type definitions with type, description, module
        """
        return self.storage.get_relationship_types()

    def get_event_types(self) -> List[Dict[str, Any]]:
        """
        Get all registered event types.

        Returns:
            List of event type definitions with type, description, module
        """
        return self.storage.get_event_types()

    def get_roll_types(self) -> List[Dict[str, Any]]:
        """
        Get all registered roll types.

        Returns:
            List of roll type definitions with type, description, module, category
        """
        return self.storage.get_roll_types()

    def get_registry_names(self) -> List[str]:
        """
        Get all registry names that have been created.

        Returns:
            List of registry names (e.g., ['magic_schools', 'damage_types'])
        """
        return self.storage.get_registry_names()

    def get_registry_values(self, registry_name: str) -> List[Dict[str, Any]]:
        """
        Get all values from a specific registry.

        Args:
            registry_name: Name of the registry to query

        Returns:
            List of dicts with keys: key, description, module, metadata
        """
        return self.storage.get_registry_values(registry_name)

    def get_registry_owner(self, registry_name: str) -> Optional[str]:
        """
        Get the module that owns a registry.

        Args:
            registry_name: Name of the registry

        Returns:
            Module name that owns this registry, or None if registry doesn't exist
        """
        return self.storage.get_registry_owner(registry_name)

    def create_registry(self, registry_name: str, module_name: str) -> 'ModuleRegistry':
        """
        Create or retrieve a cached registry for module-defined enumerated values.

        This allows modules to define custom registries without modifying core schema.
        Examples: magic_schools, damage_types, armor_types, condition_types

        **Important:** Returns the same ModuleRegistry instance for each unique
        registry_name + module_name combination. This ensures cache consistency -
        all callers share the same cache, preventing synchronization issues.

        Args:
            registry_name: Name of the registry (e.g., 'magic_schools')
            module_name: Which module owns this registry

        Returns:
            Cached ModuleRegistry instance for registering/querying values

        Example:
            # In a module's initialize() method:
            magic_registry = engine.create_registry('magic_schools', self.name)
            magic_registry.register('evocation', 'Evocation magic', {'category': 'arcane'})
            magic_registry.register('necromancy', 'Necromancy magic', {'category': 'dark'})

            # Later, same instance is returned (cache is shared):
            magic_registry2 = engine.create_registry('magic_schools', self.name)
            # magic_registry2 is magic_registry  # True!

            # Validate against registry:
            magic_registry.validate(spell_data['school'], 'spell school')
        """
        from src.modules.base import ModuleRegistry

        # Create unique key for this registry
        cache_key = f"{registry_name}:{module_name}"

        # Return cached instance if it exists
        if cache_key not in self._registry_instances:
            # Create new instance and cache it
            self._registry_instances[cache_key] = ModuleRegistry(
                registry_name, module_name, self.storage
            )

        return self._registry_instances[cache_key]

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

    # ========== Position Validation (delegates to PositionSystem) ==========

    def _validate_position_with_system(self, entity_id: str, position_data: Dict[str, Any]) -> Result:
        """
        Validate Position component data using PositionSystem.

        This is a wrapper that delegates to the PositionSystem from the core_components module.
        Keeps StateEngine generic while allowing Position-specific validation.

        Args:
            entity_id: Entity that will have this position
            position_data: Position component data to validate

        Returns:
            Result indicating success or validation error
        """
        # Get PositionSystem from core_components module
        from src.modules.core_components.systems import PositionSystem

        position_system = PositionSystem(self)
        return position_system.validate_position_data(entity_id, position_data)

    # ========== AI Context Generation ==========

    def generate_ai_context(
        self,
        entity_id: str,
        include_history: bool = True,
        include_events: bool = True,
        include_nearby: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive AI context for an entity.

        Builds a structured representation of game state optimized for
        LLM consumption. Includes character stats, location, inventory,
        conversation history, and recent events.

        Args:
            entity_id: ID of the entity to build context for
            include_history: Include conversation history (default: True)
            include_events: Include recent game events (default: True)
            include_nearby: Include nearby entities (default: True)

        Returns:
            Dict with comprehensive game state context:
            {
                'character': {...},      # Stats, class, level, etc.
                'location': {...},       # Current location and nearby entities
                'inventory': [...],      # Items owned/equipped
                'conversation': [...],   # Recent messages (if include_history)
                'recent_events': [...]   # Recent game events (if include_events)
            }

        Example:
            >>> context = engine.generate_ai_context('entity_123')
            >>> print(context['character']['name'])
            'Theron the Brave'
            >>> print(context['character']['level'])
            5
            >>> print(len(context['conversation']))
            10

        Note:
            This method is optimized for AI DM functionality. The context
            includes only information that's relevant for narrative generation
            and action suggestions.
        """
        from .ai_context import AIContextBuilder

        builder = AIContextBuilder(self)
        return builder.build_full_context(
            entity_id=entity_id,
            include_history=include_history,
            include_events=include_events,
            include_nearby=include_nearby
        )

    def close(self) -> None:
        """Close storage connection."""
        self.storage.close()
