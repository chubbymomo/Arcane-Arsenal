"""
Core data models for Arcane Arsenal ECS system.

These models represent the fundamental building blocks:
- Entity: Container with ID and name
- Component: Typed data attached to entities
- Relationship: Explicit connection between entities
- Event: Immutable record of state changes
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import json


def generate_id(prefix: str) -> str:
    """
    Generate a unique ID with the given prefix.
    
    Args:
        prefix: Prefix for the ID (e.g., 'entity', 'component', 'evt')
        
    Returns:
        String like 'entity_a1b2c3d4e5f6'
    
    Examples:
        >>> generate_id('entity')
        'entity_a1b2c3d4e5f6'
    """
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


@dataclass
class Entity:
    """
    An entity in the ECS system.
    
    Entities are minimal containers - all real data lives in components.
    Think of an entity as just an ID that components can attach to.
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        created_at: When this entity was created
        modified_at: When this entity was last modified
        deleted_at: When this entity was soft-deleted (None if active)
        deleted_by: Who deleted this entity (entity_id or 'system')
    """
    id: str
    name: str
    created_at: datetime
    modified_at: datetime
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @staticmethod
    def create(name: str, entity_id: str = None) -> 'Entity':
        """
        Create a new entity with generated ID and timestamps.
        
        Args:
            name: Entity name
            entity_id: Optional specific ID (generated if not provided)
            
        Returns:
            New Entity instance
        """
        timestamp = now()
        return Entity(
            id=entity_id or generate_id('entity'),
            name=name,
            created_at=timestamp,
            modified_at=timestamp
        )
    
    def is_active(self) -> bool:
        """Check if entity is active (not soft-deleted)."""
        return self.deleted_at is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'deleted_by': self.deleted_by
        }


@dataclass
class Component:
    """
    A component attached to an entity.
    
    Components are typed data containers. All entity data lives here.
    The component_type determines what kind of data this is and what schema validates it.
    
    Attributes:
        id: Unique identifier
        entity_id: Which entity this component belongs to
        component_type: Type of component (must be registered)
        data: Component data as dictionary (validated against type's schema)
        version: Update counter (increments on each modification)
        created_at: When this component was created
        modified_at: When this component was last modified
        deleted_at: When this component was soft-deleted (None if active)
    
    Examples:
        Health component: type='Health', data={'current': 25, 'max': 30}
        Position component: type='Position', data={'x': 100, 'y': 200, 'z': 0}
    """
    id: str
    entity_id: str
    component_type: str
    data: Dict[str, Any]
    version: int
    created_at: datetime
    modified_at: datetime
    deleted_at: Optional[datetime] = None
    
    @staticmethod
    def create(entity_id: str, component_type: str, data: Dict[str, Any],
               component_id: str = None) -> 'Component':
        """
        Create a new component.
        
        Args:
            entity_id: Entity to attach to
            component_type: Type of component
            data: Component data
            component_id: Optional specific ID
            
        Returns:
            New Component instance
        """
        timestamp = now()
        return Component(
            id=component_id or generate_id('comp'),
            entity_id=entity_id,
            component_type=component_type,
            data=data,
            version=1,
            created_at=timestamp,
            modified_at=timestamp
        )
    
    def is_active(self) -> bool:
        """Check if component is active (not soft-deleted)."""
        return self.deleted_at is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'entity_id': self.entity_id,
            'component_type': self.component_type,
            'data': self.data,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }


@dataclass
class Relationship:
    """
    An explicit directed relationship between two entities.
    
    Relationships connect entities in a typed way: from_entity -> to_entity.
    The relationship_type determines the semantics (e.g., 'located_at', 'knows').
    
    Attributes:
        id: Unique identifier
        from_entity: Source entity ID
        to_entity: Target entity ID
        relationship_type: Type of relationship (must be registered)
        metadata: Optional additional data about this relationship
        created_at: When this relationship was created
        deleted_at: When this relationship was soft-deleted (None if active)
    
    Examples:
        Character in location: from='char_123', to='loc_tavern', type='located_at'
        Character knows NPC: from='char_123', to='npc_456', type='knows',
                            metadata={'trust_level': 8}
    """
    id: str
    from_entity: str
    to_entity: str
    relationship_type: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    deleted_at: Optional[datetime] = None
    
    @staticmethod
    def create(from_entity: str, to_entity: str, relationship_type: str,
               metadata: Optional[Dict[str, Any]] = None,
               relationship_id: str = None) -> 'Relationship':
        """
        Create a new relationship.
        
        Args:
            from_entity: Source entity ID
            to_entity: Target entity ID
            relationship_type: Type of relationship
            metadata: Optional metadata
            relationship_id: Optional specific ID
            
        Returns:
            New Relationship instance
        """
        return Relationship(
            id=relationship_id or generate_id('rel'),
            from_entity=from_entity,
            to_entity=to_entity,
            relationship_type=relationship_type,
            metadata=metadata or {},
            created_at=now()
        )
    
    def is_active(self) -> bool:
        """Check if relationship is active (not soft-deleted)."""
        return self.deleted_at is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'from_entity': self.from_entity,
            'to_entity': self.to_entity,
            'relationship_type': self.relationship_type,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }


@dataclass
class Event:
    """
    An immutable record of a state change.
    
    Events provide a complete audit trail of everything that happens in the world.
    They enable undo/redo, debugging, and network synchronization.
    
    Attributes:
        event_id: Unique identifier
        timestamp: When this event occurred
        event_type: Type of event (must be registered)
        entity_id: Entity involved (if any)
        component_id: Component involved (if any)
        actor_id: Who/what caused this event
        data: Event-specific data (delta/change information)
    
    Examples:
        Entity created: type='entity.created', entity_id='char_123',
                       data={'name': 'Theron'}
        Component updated: type='component.updated', entity_id='char_123',
                          component_id='comp_456', data={'field': 'hp', 'old': 30, 'new': 25}
    """
    event_id: str
    timestamp: datetime
    event_type: str
    entity_id: Optional[str]
    component_id: Optional[str]
    actor_id: Optional[str]
    data: Dict[str, Any]
    
    @staticmethod
    def create(event_type: str, data: Dict[str, Any],
               entity_id: Optional[str] = None,
               component_id: Optional[str] = None,
               actor_id: Optional[str] = None,
               event_id: str = None) -> 'Event':
        """
        Create a new event.
        
        Args:
            event_type: Type of event
            data: Event data
            entity_id: Related entity (optional)
            component_id: Related component (optional)
            actor_id: Who caused this (optional)
            event_id: Optional specific ID
            
        Returns:
            New Event instance
        """
        return Event(
            event_id=event_id or generate_id('evt'),
            timestamp=now(),
            event_type=event_type,
            entity_id=entity_id,
            component_id=component_id,
            actor_id=actor_id,
            data=data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'entity_id': self.entity_id,
            'component_id': self.component_id,
            'actor_id': self.actor_id,
            'data': self.data
        }
