"""
Unit tests for WorldStorage class.
"""

import pytest
import os
from datetime import datetime
from src.core.storage import WorldStorage
from src.core.models import Entity, Component, Relationship, Event


@pytest.fixture
def storage():
    """Create an in-memory storage for testing."""
    storage = WorldStorage(':memory:')
    storage.initialize()
    yield storage
    storage.close()


class TestWorldStorage:
    """Test WorldStorage initialization and basic operations."""
    
    def test_initialize(self, storage):
        """Test that database initializes with correct tables."""
        cursor = storage.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'entities' in tables
        assert 'components' in tables
        assert 'relationships' in tables
        assert 'events' in tables
        assert 'component_types' in tables
        assert 'relationship_types' in tables
        assert 'event_types' in tables


class TestTypeRegistry:
    """Test type registry operations."""
    
    def test_register_component_type(self, storage):
        """Test registering a component type."""
        storage.register_component_type(
            'Health',
            'Health component',
            '1.0.0',
            'core'
        )
        
        types = storage.get_component_types()
        assert len(types) > 0
        health_type = next((t for t in types if t['type'] == 'Health'), None)
        assert health_type is not None
        assert health_type['description'] == 'Health component'
        
    def test_register_relationship_type(self, storage):
        """Test registering a relationship type."""
        storage.register_relationship_type(
            'knows',
            'Character knows another character',
            'core'
        )
        
        types = storage.get_relationship_types()
        knows_type = next((t for t in types if t['type'] == 'knows'), None)
        assert knows_type is not None
        
    def test_register_event_type(self, storage):
        """Test registering an event type."""
        storage.register_event_type(
            'entity.created',
            'Entity was created',
            'core'
        )
        
        types = storage.get_event_types()
        event_type = next((t for t in types if t['type'] == 'entity.created'), None)
        assert event_type is not None


class TestEntityOperations:
    """Test entity CRUD operations."""
    
    def test_save_and_get_entity(self, storage):
        """Test saving and retrieving an entity."""
        entity = Entity.create('Test Entity')
        
        assert storage.save_entity(entity) is True
        
        retrieved = storage.get_entity(entity.id)
        assert retrieved is not None
        assert retrieved.id == entity.id
        assert retrieved.name == 'Test Entity'
        
    def test_get_nonexistent_entity(self, storage):
        """Test retrieving an entity that doesn't exist."""
        result = storage.get_entity('nonexistent')
        assert result is None
        
    def test_list_entities(self, storage):
        """Test listing all entities."""
        entity1 = Entity.create('Entity 1')
        entity2 = Entity.create('Entity 2')
        
        storage.save_entity(entity1)
        storage.save_entity(entity2)
        
        entities = storage.list_entities()
        assert len(entities) >= 2
        names = [e.name for e in entities]
        assert 'Entity 1' in names
        assert 'Entity 2' in names
        
    def test_soft_delete_entity(self, storage):
        """Test soft-deleting an entity."""
        entity = Entity.create('To Delete')
        storage.save_entity(entity)
        
        assert storage.soft_delete_entity(entity.id, 'system') is True
        
        # Should still exist in database
        retrieved = storage.get_entity(entity.id)
        assert retrieved is not None
        assert retrieved.deleted_at is not None
        assert retrieved.deleted_by == 'system'
        
        # Should not appear in list by default
        entities = storage.list_entities(include_deleted=False)
        assert entity.id not in [e.id for e in entities]
        
        # Should appear when including deleted
        entities = storage.list_entities(include_deleted=True)
        assert entity.id in [e.id for e in entities]
        
    def test_restore_entity(self, storage):
        """Test restoring a soft-deleted entity."""
        entity = Entity.create('To Restore')
        storage.save_entity(entity)
        storage.soft_delete_entity(entity.id, 'system')
        
        assert storage.restore_entity(entity.id) is True
        
        retrieved = storage.get_entity(entity.id)
        assert retrieved.deleted_at is None
        assert retrieved.deleted_by is None


class TestComponentOperations:
    """Test component CRUD operations."""
    
    def test_save_and_get_component(self, storage):
        """Test saving and retrieving a component."""
        entity = Entity.create('Test Entity')
        storage.save_entity(entity)
        
        # Register component type first
        storage.register_component_type('Health', 'Health', '1.0.0', 'test')
        
        component = Component.create(
            entity.id,
            'Health',
            {'current': 25, 'max': 30}
        )
        
        assert storage.save_component(component) is True
        
        retrieved = storage.get_component(entity.id, 'Health')
        assert retrieved is not None
        assert retrieved.entity_id == entity.id
        assert retrieved.component_type == 'Health'
        assert retrieved.data == {'current': 25, 'max': 30}
        
    def test_get_entity_components(self, storage):
        """Test getting all components for an entity."""
        entity = Entity.create('Test Entity')
        storage.save_entity(entity)
        
        storage.register_component_type('Health', 'Health', '1.0.0', 'test')
        storage.register_component_type('Position', 'Position', '1.0.0', 'test')
        
        comp1 = Component.create(entity.id, 'Health', {'current': 25})
        comp2 = Component.create(entity.id, 'Position', {'x': 10, 'y': 20})
        
        storage.save_component(comp1)
        storage.save_component(comp2)
        
        components = storage.get_entity_components(entity.id)
        assert len(components) == 2
        types = [c.component_type for c in components]
        assert 'Health' in types
        assert 'Position' in types
        
    def test_list_components_by_type(self, storage):
        """Test listing all components of a specific type."""
        entity1 = Entity.create('Entity 1')
        entity2 = Entity.create('Entity 2')
        storage.save_entity(entity1)
        storage.save_entity(entity2)
        
        storage.register_component_type('Health', 'Health', '1.0.0', 'test')
        
        comp1 = Component.create(entity1.id, 'Health', {'current': 25})
        comp2 = Component.create(entity2.id, 'Health', {'current': 30})
        
        storage.save_component(comp1)
        storage.save_component(comp2)
        
        components = storage.list_components_by_type('Health')
        assert len(components) == 2
        
    def test_delete_component(self, storage):
        """Test soft-deleting a component."""
        entity = Entity.create('Test Entity')
        storage.save_entity(entity)
        
        storage.register_component_type('Health', 'Health', '1.0.0', 'test')
        
        component = Component.create(entity.id, 'Health', {'current': 25})
        storage.save_component(component)
        
        assert storage.delete_component(component.id) is True
        
        # Should not be retrievable
        retrieved = storage.get_component(entity.id, 'Health')
        assert retrieved is None


class TestRelationshipOperations:
    """Test relationship CRUD operations."""
    
    def test_save_and_get_relationship(self, storage):
        """Test saving and retrieving a relationship."""
        entity1 = Entity.create('Entity 1')
        entity2 = Entity.create('Entity 2')
        storage.save_entity(entity1)
        storage.save_entity(entity2)
        
        storage.register_relationship_type('knows', 'Knows', 'test')
        
        rel = Relationship.create(
            entity1.id,
            entity2.id,
            'knows',
            {'trust_level': 8}
        )
        
        assert storage.save_relationship(rel) is True
        
        retrieved = storage.get_relationship(rel.id)
        assert retrieved is not None
        assert retrieved.from_entity == entity1.id
        assert retrieved.to_entity == entity2.id
        assert retrieved.relationship_type == 'knows'
        assert retrieved.metadata['trust_level'] == 8
        
    def test_get_entity_relationships(self, storage):
        """Test getting relationships for an entity."""
        entity1 = Entity.create('Entity 1')
        entity2 = Entity.create('Entity 2')
        entity3 = Entity.create('Entity 3')
        storage.save_entity(entity1)
        storage.save_entity(entity2)
        storage.save_entity(entity3)
        
        storage.register_relationship_type('knows', 'Knows', 'test')
        
        # entity1 -> entity2
        rel1 = Relationship.create(entity1.id, entity2.id, 'knows')
        # entity3 -> entity1
        rel2 = Relationship.create(entity3.id, entity1.id, 'knows')
        
        storage.save_relationship(rel1)
        storage.save_relationship(rel2)
        
        # Get relationships from entity1
        rels = storage.get_entity_relationships(entity1.id, direction='from')
        assert len(rels) == 1
        assert rels[0].to_entity == entity2.id
        
        # Get relationships to entity1
        rels = storage.get_entity_relationships(entity1.id, direction='to')
        assert len(rels) == 1
        assert rels[0].from_entity == entity3.id
        
        # Get all relationships involving entity1
        rels = storage.get_entity_relationships(entity1.id, direction='both')
        assert len(rels) == 2
        
    def test_delete_relationship(self, storage):
        """Test soft-deleting a relationship."""
        entity1 = Entity.create('Entity 1')
        entity2 = Entity.create('Entity 2')
        storage.save_entity(entity1)
        storage.save_entity(entity2)
        
        storage.register_relationship_type('knows', 'Knows', 'test')
        
        rel = Relationship.create(entity1.id, entity2.id, 'knows')
        storage.save_relationship(rel)
        
        assert storage.delete_relationship(rel.id) is True
        
        # Should still exist but marked deleted
        retrieved = storage.get_relationship(rel.id)
        assert retrieved is not None
        assert retrieved.deleted_at is not None
        
        # Should not appear in entity relationships
        rels = storage.get_entity_relationships(entity1.id)
        assert len(rels) == 0


class TestEventOperations:
    """Test event logging and retrieval."""
    
    def test_log_and_get_events(self, storage):
        """Test logging and retrieving events."""
        storage.register_event_type('test.event', 'Test event', 'test')
        
        event = Event.create(
            'test.event',
            {'message': 'Test'},
            entity_id='entity_123',
            actor_id='system'
        )
        
        storage.log_event(event)
        
        events = storage.get_events()
        assert len(events) >= 1
        
        retrieved = next((e for e in events if e.event_id == event.event_id), None)
        assert retrieved is not None
        assert retrieved.event_type == 'test.event'
        assert retrieved.entity_id == 'entity_123'
        
    def test_get_events_filtered(self, storage):
        """Test retrieving events with filters."""
        storage.register_event_type('type1', 'Type 1', 'test')
        storage.register_event_type('type2', 'Type 2', 'test')
        
        event1 = Event.create('type1', {}, entity_id='entity_1')
        event2 = Event.create('type2', {}, entity_id='entity_1')
        event3 = Event.create('type1', {}, entity_id='entity_2')
        
        storage.log_event(event1)
        storage.log_event(event2)
        storage.log_event(event3)
        
        # Filter by entity
        events = storage.get_events(entity_id='entity_1')
        assert len(events) == 2
        
        # Filter by type
        events = storage.get_events(event_type='type1')
        assert len(events) == 2


class TestQueryOperations:
    """Test query operations."""
    
    def test_query_entities_by_component(self, storage):
        """Test querying entities by component types."""
        entity1 = Entity.create('Entity 1')
        entity2 = Entity.create('Entity 2')
        entity3 = Entity.create('Entity 3')
        storage.save_entity(entity1)
        storage.save_entity(entity2)
        storage.save_entity(entity3)
        
        storage.register_component_type('Health', 'Health', '1.0.0', 'test')
        storage.register_component_type('Position', 'Position', '1.0.0', 'test')
        
        # entity1: Health + Position
        storage.save_component(Component.create(entity1.id, 'Health', {}))
        storage.save_component(Component.create(entity1.id, 'Position', {}))
        
        # entity2: Health only
        storage.save_component(Component.create(entity2.id, 'Health', {}))
        
        # entity3: Position only
        storage.save_component(Component.create(entity3.id, 'Position', {}))
        
        # Query for entities with Health
        entities = storage.query_entities(['Health'])
        entity_ids = [e.id for e in entities]
        assert entity1.id in entity_ids
        assert entity2.id in entity_ids
        assert entity3.id not in entity_ids
        
        # Query for entities with both Health and Position
        entities = storage.query_entities(['Health', 'Position'])
        entity_ids = [e.id for e in entities]
        assert entity1.id in entity_ids
        assert entity2.id not in entity_ids
        assert entity3.id not in entity_ids


class TestTransactions:
    """Test transaction management."""
    
    def test_transaction_commit(self, storage):
        """Test committing a transaction."""
        storage.begin_transaction()
        
        entity = Entity.create('Test')
        storage.save_entity(entity)
        
        storage.commit()
        
        # Should be persisted
        retrieved = storage.get_entity(entity.id)
        assert retrieved is not None
        
    def test_transaction_rollback(self, storage):
        """Test rolling back a transaction."""
        storage.begin_transaction()
        
        entity = Entity.create('Test')
        storage.conn.execute("""
            INSERT INTO entities (id, name, created_at, modified_at)
            VALUES (?, ?, ?, ?)
        """, (entity.id, entity.name, entity.created_at, entity.modified_at))
        
        storage.rollback()
        
        # Should not be persisted
        retrieved = storage.get_entity(entity.id)
        assert retrieved is None
