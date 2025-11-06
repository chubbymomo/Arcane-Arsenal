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


def test_hierarchical_positioning(world_path):
    """Test hierarchical positioning for nested spaces."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    # Create tavern at absolute world position
    tavern_result = engine.create_entity('The Golden Tankard')
    tavern_id = tavern_result.data['id']
    engine.add_component(tavern_id, 'Position', {
        'x': 100,
        'y': 200,
        'z': 0,
        'region': 'overworld'
    })

    # Create table inside tavern (relative position)
    table_result = engine.create_entity('Wooden Table')
    table_id = table_result.data['id']
    engine.add_component(table_id, 'Position', {
        'x': 5,
        'y': 3,
        'z': 0,
        'region': tavern_id
    })

    # Create mug on table (nested position)
    mug_result = engine.create_entity('Ale Mug')
    mug_id = mug_result.data['id']
    engine.add_component(mug_id, 'Position', {
        'x': 0.5,
        'y': 0.5,
        'z': 1.2,
        'region': table_id
    })

    # Test get_world_position() for absolute position
    tavern_pos = engine.get_world_position(tavern_id)
    assert tavern_pos == (100.0, 200.0, 0.0)

    # Test get_world_position() for relative position (table in tavern)
    table_pos = engine.get_world_position(table_id)
    assert table_pos == (105.0, 203.0, 0.0)

    # Test get_world_position() for nested position (mug on table)
    mug_pos = engine.get_world_position(mug_id)
    assert mug_pos == (105.5, 203.5, 1.2)

    # Test get_entities_in_region() for tavern
    entities_in_tavern = engine.get_entities_in_region(tavern_id)
    assert len(entities_in_tavern) == 1
    assert entities_in_tavern[0].id == table_id

    # Test get_entities_in_region() for table
    entities_on_table = engine.get_entities_in_region(table_id)
    assert len(entities_on_table) == 1
    assert entities_on_table[0].id == mug_id

    # Test get_entities_in_region() for named region
    entities_in_overworld = engine.get_entities_in_region('overworld')
    assert len(entities_in_overworld) == 1
    assert entities_in_overworld[0].id == tavern_id

    # Test entity without Position component
    no_pos_result = engine.create_entity('Abstract Entity')
    no_pos_id = no_pos_result.data['id']
    assert engine.get_world_position(no_pos_id) is None

    # Test circular reference detection
    circular_result = engine.create_entity('Circular Entity')
    circular_id = circular_result.data['id']
    engine.add_component(circular_id, 'Position', {
        'x': 10,
        'y': 10,
        'z': 0,
        'region': circular_id  # Points to itself
    })
    # Should return None when circular reference detected
    assert engine.get_world_position(circular_id) is None


def test_spatial_validation(world_path):
    """Test spatial validation for Position components."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    # Create parent entity with Position
    parent_result = engine.create_entity('Parent Room')
    parent_id = parent_result.data['id']
    engine.add_component(parent_id, 'Position', {
        'x': 0,
        'y': 0,
        'z': 0,
        'region': 'building'
    })

    # Create child entity
    child_result = engine.create_entity('Child Table')
    child_id = child_result.data['id']

    # Test: Valid position relative to parent
    result = engine.add_component(child_id, 'Position', {
        'x': 5,
        'y': 5,
        'z': 0,
        'region': parent_id
    })
    assert result.success is True

    # Test: Cannot position relative to non-existent entity
    orphan_result = engine.create_entity('Orphan')
    orphan_id = orphan_result.data['id']
    result = engine.add_component(orphan_id, 'Position', {
        'x': 0,
        'y': 0,
        'z': 0,
        'region': 'entity_nonexistent'
    })
    assert result.success is False
    assert result.error_code == 'INVALID_PARENT'

    # Test: Cannot position relative to entity without Position
    no_pos_result = engine.create_entity('No Position Entity')
    no_pos_id = no_pos_result.data['id']

    bad_child_result = engine.create_entity('Bad Child')
    bad_child_id = bad_child_result.data['id']
    result = engine.add_component(bad_child_id, 'Position', {
        'x': 0,
        'y': 0,
        'z': 0,
        'region': no_pos_id
    })
    assert result.success is False
    assert result.error_code == 'INVALID_PARENT'

    # Test: Cannot create circular reference (direct)
    result = engine.update_component(parent_id, 'Position', {
        'x': 0,
        'y': 0,
        'z': 0,
        'region': parent_id  # Points to itself
    })
    assert result.success is False
    assert result.error_code == 'CIRCULAR_REFERENCE'

    # Test: Cannot create circular reference (indirect)
    result = engine.update_component(parent_id, 'Position', {
        'x': 0,
        'y': 0,
        'z': 0,
        'region': child_id  # Child is already in parent
    })
    assert result.success is False
    assert result.error_code == 'CIRCULAR_REFERENCE'


def test_container_component(world_path):
    """Test Container component and capacity validation."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    # Create chest with limited capacity
    chest_result = engine.create_entity('Wooden Chest')
    chest_id = chest_result.data['id']
    engine.add_component(chest_id, 'Position', {
        'x': 10,
        'y': 10,
        'z': 0,
        'region': 'tavern'
    })

    # Add Container component with capacity of 2
    result = engine.add_component(chest_id, 'Container', {'capacity': 2})
    assert result.success is True

    # Create bag of holding (unlimited capacity)
    bag_result = engine.create_entity('Bag of Holding')
    bag_id = bag_result.data['id']
    engine.add_component(bag_id, 'Position', {
        'x': 0,
        'y': 0,
        'z': 0,
        'region': 'overworld'
    })
    result = engine.add_component(bag_id, 'Container', {'capacity': None})
    assert result.success is True

    # Test: can_add_to_region for empty chest
    result = engine.can_add_to_region(chest_id)
    assert result.success is True

    # Add first item to chest
    item1_result = engine.create_entity('Sword')
    item1_id = item1_result.data['id']
    engine.add_component(item1_id, 'Position', {
        'x': 0,
        'y': 0,
        'z': 0,
        'region': chest_id
    })

    # Test: count_entities_in_region
    count = engine.count_entities_in_region(chest_id)
    assert count == 1

    # Add second item to chest
    item2_result = engine.create_entity('Shield')
    item2_id = item2_result.data['id']
    engine.add_component(item2_id, 'Position', {
        'x': 0,
        'y': 0,
        'z': 0,
        'region': chest_id
    })

    count = engine.count_entities_in_region(chest_id)
    assert count == 2

    # Test: can_add_to_region when at capacity
    result = engine.can_add_to_region(chest_id)
    assert result.success is False
    assert result.error_code == 'REGION_FULL'

    # Test: bag of holding never full
    for i in range(10):
        item_result = engine.create_entity(f'Item {i}')
        item_id = item_result.data['id']
        result = engine.can_add_to_region(bag_id)
        assert result.success is True  # Always succeeds
        engine.add_component(item_id, 'Position', {
            'x': 0,
            'y': 0,
            'z': 0,
            'region': bag_id
        })

    count = engine.count_entities_in_region(bag_id)
    assert count == 10

    # Can still add more
    result = engine.can_add_to_region(bag_id)
    assert result.success is True


def test_container_validation(world_path):
    """Test Container component validation."""
    engine = StateEngine.initialize_world(world_path, 'Test World')

    entity_result = engine.create_entity('Test Container')
    entity_id = entity_result.data['id']

    # Test: Valid container with capacity
    result = engine.add_component(entity_id, 'Container', {'capacity': 10})
    assert result.success is True

    # Remove for next test
    engine.remove_component(entity_id, 'Container')

    # Test: Valid container with unlimited capacity
    result = engine.add_component(entity_id, 'Container', {'capacity': None})
    assert result.success is True

    engine.remove_component(entity_id, 'Container')

    # Test: Invalid - negative capacity
    result = engine.add_component(entity_id, 'Container', {'capacity': -1})
    assert result.success is False
    assert result.error_code == 'VALIDATION_ERROR'

    # Test: Invalid - missing capacity field
    result = engine.add_component(entity_id, 'Container', {})
    assert result.success is False
    assert result.error_code == 'VALIDATION_ERROR'

    # Test: Invalid - extra fields not allowed
    result = engine.add_component(entity_id, 'Container', {
        'capacity': 10,
        'extra_field': 'not allowed'
    })
    assert result.success is False
    assert result.error_code == 'VALIDATION_ERROR'
