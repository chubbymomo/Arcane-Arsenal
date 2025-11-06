"""
Integration tests for complete workflows.
"""

import pytest
import tempfile
import shutil
from src.core.state_engine import StateEngine


@pytest.fixture
def engine():
    """Create temporary world with state engine."""
    temp_dir = tempfile.mkdtemp()
    engine = StateEngine.initialize_world(temp_dir, 'Test World')
    yield engine
    shutil.rmtree(temp_dir)


def test_complete_rpg_workflow(engine):
    """Test complete RPG workflow: create character, location, items, and relationships."""

    # Create a character
    result = engine.create_entity('Theron the Brave')
    assert result.success
    char_id = result.data['id']

    # Add Identity component
    result = engine.add_component(
        char_id,
        'Identity',
        {
            'description': 'A brave warrior seeking adventure'
        }
    )
    assert result.success

    # Add Position component
    result = engine.add_component(
        char_id,
        'Position',
        {'x': 100, 'y': 200, 'z': 0, 'region': 'tavern'}
    )
    assert result.success

    # Create a location
    result = engine.create_entity('The Golden Tankard Tavern')
    assert result.success
    tavern_id = result.data['id']

    result = engine.add_component(
        tavern_id,
        'Identity',
        {
            'description': 'A cozy tavern filled with adventurers'
        }
    )
    assert result.success

    result = engine.add_component(
        tavern_id,
        'Position',
        {'x': 100, 'y': 200, 'z': 0, 'region': 'town_center'}
    )
    assert result.success

    # Create a relationship: character is located at tavern
    result = engine.create_relationship(
        char_id,
        tavern_id,
        'located_at',
        {'since': '2024-01-15', 'reason': 'resting'}
    )
    assert result.success

    # Create an item
    result = engine.create_entity('Rusty Sword')
    assert result.success
    sword_id = result.data['id']

    result = engine.add_component(
        sword_id,
        'Identity',
        {
            'description': 'An old but serviceable weapon'
        }
    )
    assert result.success

    # Create relationship: tavern contains sword
    result = engine.create_relationship(
        tavern_id,
        sword_id,
        'contains'
    )
    assert result.success

    # Verify the world state
    # 1. Check that we have 4 entities (System + 3 created)
    entities = engine.list_entities()
    assert len(entities) == 4

    # 2. Check character has both components
    components = engine.get_entity_components(char_id)
    assert 'Identity' in components
    assert 'Position' in components

    # 3. Check character is located at tavern
    char_rels = engine.get_relationships(char_id, rel_type='located_at')
    assert len(char_rels) == 1
    assert char_rels[0].to_entity == tavern_id

    # 4. Check tavern contains sword
    tavern_rels = engine.get_relationships(tavern_id, rel_type='contains')
    assert len(tavern_rels) == 1
    assert tavern_rels[0].to_entity == sword_id

    # 5. Check events were logged
    events = engine.get_events(limit=50)
    assert len(events) > 0

    # Check for specific event types
    event_types = set(e.event_type for e in events)
    assert 'world.created' in event_types
    assert 'entity.created' in event_types
    assert 'component.added' in event_types
    assert 'relationship.created' in event_types


def test_character_movement_workflow(engine):
    """Test character moving between locations."""

    # Create character
    result = engine.create_entity('Wanderer')
    char_id = result.data['id']

    # Create two locations
    result = engine.create_entity('Forest')
    forest_id = result.data['id']

    result = engine.create_entity('Cave')
    cave_id = result.data['id']

    # Character starts in forest
    result = engine.create_relationship(char_id, forest_id, 'located_at')
    rel1_id = result.data['id']
    assert result.success

    # Character moves to cave
    result = engine.delete_relationship(rel1_id)
    assert result.success

    result = engine.create_relationship(char_id, cave_id, 'located_at')
    assert result.success

    # Verify character is now in cave
    relationships = engine.get_relationships(char_id, rel_type='located_at')
    assert len(relationships) == 1
    assert relationships[0].to_entity == cave_id

    # Verify movement events
    events = engine.get_events(entity_id=char_id)
    rel_created = [e for e in events if e.event_type == 'relationship.created']
    rel_deleted = [e for e in events if e.event_type == 'relationship.deleted']

    assert len(rel_created) == 2  # created twice
    assert len(rel_deleted) == 1  # deleted once


def test_query_by_components(engine):
    """Test querying entities by component types."""

    # Create entities with different component combinations
    result = engine.create_entity('Entity with Identity')
    e1_id = result.data['id']
    engine.add_component(e1_id, 'Identity', {'description': 'Test 1'})

    result = engine.create_entity('Entity with Position')
    e2_id = result.data['id']
    engine.add_component(e2_id, 'Position', {'x': 0, 'y': 0})

    result = engine.create_entity('Entity with Both')
    e3_id = result.data['id']
    engine.add_component(e3_id, 'Identity', {'description': 'Test 3'})
    engine.add_component(e3_id, 'Position', {'x': 10, 'y': 10})

    # Query for entities with Identity
    entities = engine.query_entities(['Identity'])
    entity_ids = [e.id for e in entities]
    assert e1_id in entity_ids
    assert e3_id in entity_ids
    assert e2_id not in entity_ids

    # Query for entities with both Identity and Position
    entities = engine.query_entities(['Identity', 'Position'])
    entity_ids = [e.id for e in entities]
    assert e3_id in entity_ids
    assert e1_id not in entity_ids
    assert e2_id not in entity_ids
