"""
Unit tests for WorldStorage.
"""

import pytest
from datetime import datetime
from src.core.storage import WorldStorage
from src.core.models import Entity, Component, Relationship, Event


@pytest.fixture
def storage():
    """Create in-memory storage for testing."""
    storage = WorldStorage(':memory:')
    storage.initialize()
    return storage


def test_entity_crud(storage):
    """Test entity CRUD operations."""
    # Create entity
    entity = Entity.create('Test Entity')
    assert storage.save_entity(entity) is True

    # Read entity
    retrieved = storage.get_entity(entity.id)
    assert retrieved is not None
    assert retrieved.name == 'Test Entity'

    # Update entity
    entity.name = 'Updated Entity'
    assert storage.save_entity(entity) is True
    retrieved = storage.get_entity(entity.id)
    assert retrieved.name == 'Updated Entity'

    # List entities
    entities = storage.list_entities()
    assert len(entities) >= 1

    # Soft delete
    assert storage.soft_delete_entity(entity.id, 'system') is True
    retrieved = storage.get_entity(entity.id)
    assert retrieved.deleted_at is not None

    # Restore
    assert storage.restore_entity(entity.id) is True
    retrieved = storage.get_entity(entity.id)
    assert retrieved.deleted_at is None


def test_component_crud(storage):
    """Test component CRUD operations."""
    # Create entity
    entity = Entity.create('Test Entity')
    storage.save_entity(entity)

    # Create component
    component = Component.create(
        entity.id,
        'TestComponent',
        {'value': 42}
    )
    assert storage.save_component(component) is True

    # Read component
    retrieved = storage.get_component(entity.id, 'TestComponent')
    assert retrieved is not None
    assert retrieved.data['value'] == 42

    # Get all entity components
    components = storage.get_entity_components(entity.id)
    assert len(components) == 1

    # Update component
    component.data = {'value': 100}
    component.version += 1
    assert storage.save_component(component) is True
    retrieved = storage.get_component(entity.id, 'TestComponent')
    assert retrieved.data['value'] == 100

    # Delete component
    assert storage.delete_component(component.id) is True
    retrieved = storage.get_component(entity.id, 'TestComponent')
    assert retrieved is None


def test_relationship_crud(storage):
    """Test relationship CRUD operations."""
    # Create entities
    entity1 = Entity.create('Entity 1')
    entity2 = Entity.create('Entity 2')
    storage.save_entity(entity1)
    storage.save_entity(entity2)

    # Create relationship
    relationship = Relationship.create(
        entity1.id,
        entity2.id,
        'test_relationship',
        {'key': 'value'}
    )
    assert storage.save_relationship(relationship) is True

    # Read relationship
    retrieved = storage.get_relationship(relationship.id)
    assert retrieved is not None
    assert retrieved.from_entity == entity1.id
    assert retrieved.to_entity == entity2.id

    # Get entity relationships
    relationships = storage.get_entity_relationships(entity1.id)
    assert len(relationships) >= 1

    # Delete relationship
    assert storage.delete_relationship(relationship.id) is True
    retrieved = storage.get_relationship(relationship.id)
    assert retrieved.deleted_at is not None
