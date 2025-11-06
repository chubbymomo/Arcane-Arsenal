"""
Unit tests for StateEngine.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from src.core.state_engine import StateEngine


@pytest.fixture
def world_path():
    """Create temporary world directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_world_initialization(world_path):
    """Test world initialization."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    assert engine is not None
    assert Path(world_path, 'world.db').exists()

    # Verify system entity exists
    system = engine.get_entity('system')
    assert system is not None
    assert system.name == 'System'

    # Verify core types registered
    comp_types = engine.storage.get_component_types()
    assert any(t['type'] == 'Identity' for t in comp_types)
    assert any(t['type'] == 'Position' for t in comp_types)

    rel_types = engine.storage.get_relationship_types()
    assert any(t['type'] == 'located_at' for t in rel_types)
    assert any(t['type'] == 'contains' for t in rel_types)


def test_entity_operations(world_path):
    """Test entity CRUD operations."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    # Create entity
    result = engine.create_entity('Test Character')
    assert result.success is True
    entity_id = result.data['id']

    # Get entity
    entity = engine.get_entity(entity_id)
    assert entity is not None
    assert entity.name == 'Test Character'

    # Update entity
    result = engine.update_entity(entity_id, 'Updated Character')
    assert result.success is True

    entity = engine.get_entity(entity_id)
    assert entity.name == 'Updated Character'

    # Delete entity
    result = engine.delete_entity(entity_id)
    assert result.success is True

    entity = engine.get_entity(entity_id)
    assert entity.deleted_at is not None

    # Restore entity
    result = engine.restore_entity(entity_id)
    assert result.success is True

    entity = engine.get_entity(entity_id)
    assert entity.deleted_at is None


def test_component_operations(world_path):
    """Test component operations."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    # Create entity
    result = engine.create_entity('Test Character')
    entity_id = result.data['id']

    # Add Identity component
    result = engine.add_component(
        entity_id,
        'Identity',
        {'description': 'A test character'}
    )
    assert result.success is True

    # Get component
    component = engine.get_component(entity_id, 'Identity')
    assert component is not None
    assert component.data['description'] == 'A test character'

    # Update component
    result = engine.update_component(
        entity_id,
        'Identity',
        {'description': 'Updated character'}
    )
    assert result.success is True

    component = engine.get_component(entity_id, 'Identity')
    assert component.data['description'] == 'Updated character'
    assert component.version == 2

    # Remove component
    result = engine.remove_component(entity_id, 'Identity')
    assert result.success is True

    component = engine.get_component(entity_id, 'Identity')
    assert component is None


def test_relationship_operations(world_path):
    """Test relationship operations."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    # Create entities
    result1 = engine.create_entity('Character')
    char_id = result1.data['id']

    result2 = engine.create_entity('Location')
    loc_id = result2.data['id']

    # Create relationship
    result = engine.create_relationship(
        char_id,
        loc_id,
        'located_at',
        {'since': '2024-01-01'}
    )
    assert result.success is True
    rel_id = result.data['id']

    # Get relationships
    relationships = engine.get_relationships(char_id)
    assert len(relationships) == 1
    assert relationships[0].relationship_type == 'located_at'

    # Delete relationship
    result = engine.delete_relationship(rel_id)
    assert result.success is True

    relationships = engine.get_relationships(char_id)
    assert len(relationships) == 0


def test_validation(world_path):
    """Test validation logic."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    # Try to add component to non-existent entity
    result = engine.add_component(
        'nonexistent',
        'Identity',
        {'description': 'Test'}
    )
    assert result.success is False
    assert result.error_code == 'ENTITY_NOT_FOUND'

    # Try to add unregistered component type
    result1 = engine.create_entity('Test')
    entity_id = result1.data['id']

    result = engine.add_component(
        entity_id,
        'UnregisteredType',
        {'data': 'test'}
    )
    assert result.success is False
    assert result.error_code == 'TYPE_NOT_REGISTERED'

    # Try to add component with invalid data
    result = engine.add_component(
        entity_id,
        'Identity',
        {'invalid_field': 'value'}  # Missing required 'description' field
    )
    assert result.success is False
    assert result.error_code == 'VALIDATION_ERROR'


def test_events(world_path):
    """Test event generation."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    # Create entity and check events
    result = engine.create_entity('Test Entity')
    entity_id = result.data['id']

    events = engine.get_events(entity_id=entity_id)
    assert len(events) > 0
    assert events[0].event_type == 'entity.created'

    # Add component and check events
    engine.add_component(entity_id, 'Identity', {'description': 'Test'})

    events = engine.get_events(entity_id=entity_id)
    assert any(e.event_type == 'component.added' for e in events)
