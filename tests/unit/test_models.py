"""
Unit tests for core models (Entity, Component, Relationship, Event).
"""

import pytest
from datetime import datetime
from src.core.models import Entity, Component, Relationship, Event, generate_id
from src.core.result import Result


class TestGenerateId:
    """Test ID generation."""
    
    def test_generate_id_format(self):
        """Test that generated IDs have correct format."""
        entity_id = generate_id('entity')
        assert entity_id.startswith('entity_')
        assert len(entity_id) == len('entity_') + 12
        
    def test_generate_id_unique(self):
        """Test that generated IDs are unique."""
        id1 = generate_id('test')
        id2 = generate_id('test')
        assert id1 != id2


class TestEntity:
    """Test Entity model."""
    
    def test_create_entity(self):
        """Test creating a new entity."""
        entity = Entity.create('Test Entity')
        
        assert entity.id.startswith('entity_')
        assert entity.name == 'Test Entity'
        assert entity.created_at is not None
        assert entity.modified_at is not None
        assert entity.deleted_at is None
        assert entity.deleted_by is None
        
    def test_create_entity_with_id(self):
        """Test creating entity with specific ID."""
        entity = Entity.create('Test', entity_id='custom_id')
        assert entity.id == 'custom_id'
        
    def test_is_active(self):
        """Test is_active method."""
        entity = Entity.create('Test')
        assert entity.is_active() is True
        
        entity.deleted_at = datetime.utcnow()
        assert entity.is_active() is False
        
    def test_to_dict(self):
        """Test converting entity to dictionary."""
        entity = Entity.create('Test Entity')
        data = entity.to_dict()
        
        assert data['id'] == entity.id
        assert data['name'] == 'Test Entity'
        assert 'created_at' in data
        assert data['deleted_at'] is None


class TestComponent:
    """Test Component model."""
    
    def test_create_component(self):
        """Test creating a new component."""
        component = Component.create(
            entity_id='entity_123',
            component_type='Health',
            data={'current': 25, 'max': 30}
        )
        
        assert component.id.startswith('comp_')
        assert component.entity_id == 'entity_123'
        assert component.component_type == 'Health'
        assert component.data == {'current': 25, 'max': 30}
        assert component.version == 1
        assert component.created_at is not None
        assert component.deleted_at is None
        
    def test_create_component_with_id(self):
        """Test creating component with specific ID."""
        component = Component.create(
            entity_id='entity_123',
            component_type='Health',
            data={},
            component_id='custom_comp_id'
        )
        assert component.id == 'custom_comp_id'
        
    def test_is_active(self):
        """Test is_active method."""
        component = Component.create('entity_123', 'Health', {})
        assert component.is_active() is True
        
        component.deleted_at = datetime.utcnow()
        assert component.is_active() is False
        
    def test_to_dict(self):
        """Test converting component to dictionary."""
        component = Component.create(
            entity_id='entity_123',
            component_type='Health',
            data={'current': 25}
        )
        data = component.to_dict()
        
        assert data['entity_id'] == 'entity_123'
        assert data['component_type'] == 'Health'
        assert data['data'] == {'current': 25}
        assert data['version'] == 1


class TestRelationship:
    """Test Relationship model."""
    
    def test_create_relationship(self):
        """Test creating a new relationship."""
        rel = Relationship.create(
            from_entity='entity_123',
            to_entity='entity_456',
            relationship_type='knows'
        )
        
        assert rel.id.startswith('rel_')
        assert rel.from_entity == 'entity_123'
        assert rel.to_entity == 'entity_456'
        assert rel.relationship_type == 'knows'
        assert rel.metadata == {}
        assert rel.created_at is not None
        assert rel.deleted_at is None
        
    def test_create_relationship_with_metadata(self):
        """Test creating relationship with metadata."""
        rel = Relationship.create(
            from_entity='entity_123',
            to_entity='entity_456',
            relationship_type='knows',
            metadata={'trust_level': 8}
        )
        assert rel.metadata == {'trust_level': 8}
        
    def test_is_active(self):
        """Test is_active method."""
        rel = Relationship.create('entity_123', 'entity_456', 'knows')
        assert rel.is_active() is True
        
        rel.deleted_at = datetime.utcnow()
        assert rel.is_active() is False
        
    def test_to_dict(self):
        """Test converting relationship to dictionary."""
        rel = Relationship.create(
            from_entity='entity_123',
            to_entity='entity_456',
            relationship_type='knows',
            metadata={'trust': 8}
        )
        data = rel.to_dict()
        
        assert data['from_entity'] == 'entity_123'
        assert data['to_entity'] == 'entity_456'
        assert data['relationship_type'] == 'knows'
        assert data['metadata'] == {'trust': 8}


class TestEvent:
    """Test Event model."""
    
    def test_create_event(self):
        """Test creating a new event."""
        event = Event.create(
            event_type='entity.created',
            data={'name': 'Test'},
            entity_id='entity_123',
            actor_id='system'
        )
        
        assert event.event_id.startswith('evt_')
        assert event.event_type == 'entity.created'
        assert event.entity_id == 'entity_123'
        assert event.actor_id == 'system'
        assert event.data == {'name': 'Test'}
        assert event.timestamp is not None
        
    def test_create_event_minimal(self):
        """Test creating event with minimal data."""
        event = Event.create(
            event_type='world.created',
            data={}
        )
        assert event.entity_id is None
        assert event.component_id is None
        assert event.actor_id is None
        
    def test_to_dict(self):
        """Test converting event to dictionary."""
        event = Event.create(
            event_type='entity.created',
            data={'name': 'Test'},
            entity_id='entity_123'
        )
        data = event.to_dict()
        
        assert data['event_type'] == 'entity.created'
        assert data['entity_id'] == 'entity_123'
        assert data['data'] == {'name': 'Test'}


class TestResult:
    """Test Result object."""
    
    def test_ok_result(self):
        """Test successful result."""
        result = Result.ok({'value': 42})
        
        assert result.success is True
        assert result.data == {'value': 42}
        assert result.error is None
        assert result.error_code is None
        
    def test_ok_result_no_data(self):
        """Test successful result with no data."""
        result = Result.ok()
        
        assert result.success is True
        assert result.data is None
        
    def test_fail_result(self):
        """Test failed result."""
        result = Result.fail('Something went wrong', 'ERROR_CODE')
        
        assert result.success is False
        assert result.data is None
        assert result.error == 'Something went wrong'
        assert result.error_code == 'ERROR_CODE'
        
    def test_fail_result_no_code(self):
        """Test failed result without error code."""
        result = Result.fail('Error occurred')
        
        assert result.success is False
        assert result.error == 'Error occurred'
        assert result.error_code is None
        
    def test_result_as_bool(self):
        """Test using Result in boolean context."""
        ok_result = Result.ok()
        fail_result = Result.fail('Error')
        
        assert ok_result  # Can use directly in if statement
        assert bool(ok_result) is True
        
        assert not fail_result  # Can use directly in if statement
        assert bool(fail_result) is False
