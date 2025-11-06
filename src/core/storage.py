"""
Storage layer for Arcane Arsenal.

WorldStorage provides the database interface for persisting and querying
entities, components, relationships, and events. It wraps SQLite and provides
transaction support.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import Entity, Component, Relationship, Event


class WorldStorage:
    """
    Manages SQLite database for a world.
    
    Provides CRUD operations for all core data types and handles
    transaction management.
    
    Attributes:
        db_path: Path to SQLite database file
        conn: Database connection (None until initialize() is called)
    """
    
    def __init__(self, db_path: str):
        """
        Initialize storage for a world database.
        
        Args:
            db_path: Path to SQLite database file
                    Use ':memory:' for in-memory testing database
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    def initialize(self, schema_path: str = None) -> None:
        """
        Initialize database connection and create tables if they don't exist.
        
        Args:
            schema_path: Path to schema.sql file (uses default location if not provided)
        """
        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        
        # Check if tables exist
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'"
        )
        if cursor.fetchone() is None:
            # Tables don't exist, create them
            if schema_path is None:
                # Default path relative to this file
                schema_path = Path(__file__).parent.parent.parent / 'schema.sql'
            
            with open(schema_path, 'r') as f:
                schema = f.read()
            
            self.conn.executescript(schema)
            self.conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    # ========== Transaction Management ==========
    
    def begin_transaction(self) -> None:
        """Begin a transaction."""
        if self.conn:
            self.conn.execute('BEGIN')
    
    def commit(self) -> None:
        """Commit current transaction."""
        if self.conn:
            self.conn.commit()
    
    def rollback(self) -> None:
        """Rollback current transaction."""
        if self.conn:
            self.conn.rollback()
    
    # ========== Type Registry Operations ==========
    
    def register_component_type(self, type_name: str, description: str,
                               schema_version: str, module: str) -> None:
        """
        Register a new component type.
        
        Args:
            type_name: Unique name for the component type
            description: Human-readable description
            schema_version: Version of the schema (semver)
            module: Which module provides this type
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO component_types 
            (type, description, schema_version, module, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (type_name, description, schema_version, module, datetime.utcnow()))
        self.conn.commit()
    
    def register_relationship_type(self, type_name: str, description: str,
                                  module: str) -> None:
        """
        Register a new relationship type.
        
        Args:
            type_name: Unique name for the relationship type
            description: Human-readable description
            module: Which module provides this type
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO relationship_types
            (type, description, module, created_at)
            VALUES (?, ?, ?, ?)
        """, (type_name, description, module, datetime.utcnow()))
        self.conn.commit()
    
    def register_event_type(self, type_name: str, description: str,
                           module: str) -> None:
        """
        Register a new event type.
        
        Args:
            type_name: Unique name for the event type
            description: Human-readable description
            module: Which module provides this type
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO event_types
            (type, description, module, created_at)
            VALUES (?, ?, ?, ?)
        """, (type_name, description, module, datetime.utcnow()))
        self.conn.commit()

    def register_roll_type(self, type_name: str, description: str,
                          module: str, category: str = 'general') -> None:
        """
        Register a new roll type for the RNG system.

        Args:
            type_name: Unique identifier (e.g., 'attack', 'damage', 'skill_check')
            description: Human-readable description
            module: Which module provides this type
            category: Category for grouping (e.g., 'combat', 'skill', 'saving_throw')
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO roll_types
            (type, description, module, category, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (type_name, description, module, category, datetime.utcnow()))
        self.conn.commit()

    def get_roll_types(self) -> List[Dict[str, Any]]:
        """Get all registered roll types."""
        cursor = self.conn.execute("""
            SELECT type, description, module, category
            FROM roll_types
            ORDER BY category, type
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_component_types(self) -> List[Dict[str, Any]]:
        """Get all registered component types."""
        cursor = self.conn.execute("""
            SELECT type, description, schema_version, module
            FROM component_types
            ORDER BY type
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_relationship_types(self) -> List[Dict[str, Any]]:
        """Get all registered relationship types."""
        cursor = self.conn.execute("""
            SELECT type, description, module
            FROM relationship_types
            ORDER BY type
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_event_types(self) -> List[Dict[str, Any]]:
        """Get all registered event types."""
        cursor = self.conn.execute("""
            SELECT type, description, module
            FROM event_types
            ORDER BY type
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Entity CRUD ==========
    
    def save_entity(self, entity: Entity) -> bool:
        """
        Save or update an entity.
        
        Args:
            entity: Entity to save
            
        Returns:
            True if successful
        """
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO entities
                (id, name, created_at, modified_at, deleted_at, deleted_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entity.id,
                entity.name,
                entity.created_at,
                entity.modified_at,
                entity.deleted_at,
                entity.deleted_by
            ))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Retrieve an entity by ID.
        
        Args:
            entity_id: Entity ID to look up
            
        Returns:
            Entity if found, None otherwise
        """
        cursor = self.conn.execute("""
            SELECT id, name, created_at, modified_at, deleted_at, deleted_by
            FROM entities
            WHERE id = ?
        """, (entity_id,))
        
        row = cursor.fetchone()
        if row:
            return Entity(
                id=row['id'],
                name=row['name'],
                created_at=self._parse_datetime(row['created_at']),
                modified_at=self._parse_datetime(row['modified_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None,
                deleted_by=row['deleted_by']
            )
        return None
    
    def list_entities(self, include_deleted: bool = False) -> List[Entity]:
        """
        List all entities.
        
        Args:
            include_deleted: Whether to include soft-deleted entities
            
        Returns:
            List of entities
        """
        query = "SELECT id, name, created_at, modified_at, deleted_at, deleted_by FROM entities"
        if not include_deleted:
            query += " WHERE deleted_at IS NULL"
        query += " ORDER BY name"
        
        cursor = self.conn.execute(query)
        entities = []
        
        for row in cursor.fetchall():
            entities.append(Entity(
                id=row['id'],
                name=row['name'],
                created_at=self._parse_datetime(row['created_at']),
                modified_at=self._parse_datetime(row['modified_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None,
                deleted_by=row['deleted_by']
            ))
        
        return entities
    
    def soft_delete_entity(self, entity_id: str, deleted_by: str) -> bool:
        """
        Soft-delete an entity.
        
        Args:
            entity_id: Entity to delete
            deleted_by: Who is deleting it (entity_id or 'system')
            
        Returns:
            True if successful
        """
        try:
            self.conn.execute("""
                UPDATE entities
                SET deleted_at = ?, deleted_by = ?, modified_at = ?
                WHERE id = ?
            """, (datetime.utcnow(), deleted_by, datetime.utcnow(), entity_id))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def restore_entity(self, entity_id: str) -> bool:
        """
        Restore a soft-deleted entity.
        
        Args:
            entity_id: Entity to restore
            
        Returns:
            True if successful
        """
        try:
            self.conn.execute("""
                UPDATE entities
                SET deleted_at = NULL, deleted_by = NULL, modified_at = ?
                WHERE id = ?
            """, (datetime.utcnow(), entity_id))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    # ========== Component CRUD ==========
    
    def save_component(self, component: Component) -> bool:
        """
        Save or update a component.
        
        Args:
            component: Component to save
            
        Returns:
            True if successful
        """
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO components
                (id, entity_id, component_type, data, version, created_at, modified_at, deleted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                component.id,
                component.entity_id,
                component.component_type,
                json.dumps(component.data),
                component.version,
                component.created_at,
                component.modified_at,
                component.deleted_at
            ))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_component(self, entity_id: str, component_type: str) -> Optional[Component]:
        """
        Get a specific component from an entity.
        
        Args:
            entity_id: Entity ID
            component_type: Type of component to retrieve
            
        Returns:
            Component if found, None otherwise
        """
        cursor = self.conn.execute("""
            SELECT id, entity_id, component_type, data, version, created_at, modified_at, deleted_at
            FROM components
            WHERE entity_id = ? AND component_type = ? AND deleted_at IS NULL
        """, (entity_id, component_type))
        
        row = cursor.fetchone()
        if row:
            return Component(
                id=row['id'],
                entity_id=row['entity_id'],
                component_type=row['component_type'],
                data=json.loads(row['data']),
                version=row['version'],
                created_at=self._parse_datetime(row['created_at']),
                modified_at=self._parse_datetime(row['modified_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None
            )
        return None
    
    def get_entity_components(self, entity_id: str) -> List[Component]:
        """
        Get all components for an entity.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            List of components
        """
        cursor = self.conn.execute("""
            SELECT id, entity_id, component_type, data, version, created_at, modified_at, deleted_at
            FROM components
            WHERE entity_id = ? AND deleted_at IS NULL
            ORDER BY component_type
        """, (entity_id,))
        
        components = []
        for row in cursor.fetchall():
            components.append(Component(
                id=row['id'],
                entity_id=row['entity_id'],
                component_type=row['component_type'],
                data=json.loads(row['data']),
                version=row['version'],
                created_at=self._parse_datetime(row['created_at']),
                modified_at=self._parse_datetime(row['modified_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None
            ))
        
        return components
    
    def list_components_by_type(self, component_type: str) -> List[Component]:
        """
        List all components of a specific type.
        
        Args:
            component_type: Type of component
            
        Returns:
            List of components
        """
        cursor = self.conn.execute("""
            SELECT id, entity_id, component_type, data, version, created_at, modified_at, deleted_at
            FROM components
            WHERE component_type = ? AND deleted_at IS NULL
            ORDER BY entity_id
        """, (component_type,))
        
        components = []
        for row in cursor.fetchall():
            components.append(Component(
                id=row['id'],
                entity_id=row['entity_id'],
                component_type=row['component_type'],
                data=json.loads(row['data']),
                version=row['version'],
                created_at=self._parse_datetime(row['created_at']),
                modified_at=self._parse_datetime(row['modified_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None
            ))
        
        return components
    
    def delete_component(self, component_id: str) -> bool:
        """
        Soft-delete a component.
        
        Args:
            component_id: Component ID to delete
            
        Returns:
            True if successful
        """
        try:
            self.conn.execute("""
                UPDATE components
                SET deleted_at = ?, modified_at = ?
                WHERE id = ?
            """, (datetime.utcnow(), datetime.utcnow(), component_id))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    # ========== Relationship CRUD ==========
    
    def save_relationship(self, relationship: Relationship) -> bool:
        """
        Save or update a relationship.
        
        Args:
            relationship: Relationship to save
            
        Returns:
            True if successful
        """
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO relationships
                (id, from_entity, to_entity, relationship_type, metadata, created_at, deleted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                relationship.id,
                relationship.from_entity,
                relationship.to_entity,
                relationship.relationship_type,
                json.dumps(relationship.metadata) if relationship.metadata else None,
                relationship.created_at,
                relationship.deleted_at
            ))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """
        Get a relationship by ID.
        
        Args:
            relationship_id: Relationship ID
            
        Returns:
            Relationship if found, None otherwise
        """
        cursor = self.conn.execute("""
            SELECT id, from_entity, to_entity, relationship_type, metadata, created_at, deleted_at
            FROM relationships
            WHERE id = ?
        """, (relationship_id,))
        
        row = cursor.fetchone()
        if row:
            return Relationship(
                id=row['id'],
                from_entity=row['from_entity'],
                to_entity=row['to_entity'],
                relationship_type=row['relationship_type'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                created_at=self._parse_datetime(row['created_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None
            )
        return None
    
    def get_entity_relationships(self, entity_id: str,
                                direction: str = 'both') -> List[Relationship]:
        """
        Get all relationships for an entity.
        
        Args:
            entity_id: Entity ID
            direction: 'from', 'to', or 'both'
            
        Returns:
            List of relationships
        """
        if direction == 'from':
            query = """
                SELECT id, from_entity, to_entity, relationship_type, metadata, created_at, deleted_at
                FROM relationships
                WHERE from_entity = ? AND deleted_at IS NULL
            """
            params = (entity_id,)
        elif direction == 'to':
            query = """
                SELECT id, from_entity, to_entity, relationship_type, metadata, created_at, deleted_at
                FROM relationships
                WHERE to_entity = ? AND deleted_at IS NULL
            """
            params = (entity_id,)
        else:  # both
            query = """
                SELECT id, from_entity, to_entity, relationship_type, metadata, created_at, deleted_at
                FROM relationships
                WHERE (from_entity = ? OR to_entity = ?) AND deleted_at IS NULL
            """
            params = (entity_id, entity_id)
        
        cursor = self.conn.execute(query, params)
        
        relationships = []
        for row in cursor.fetchall():
            relationships.append(Relationship(
                id=row['id'],
                from_entity=row['from_entity'],
                to_entity=row['to_entity'],
                relationship_type=row['relationship_type'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                created_at=self._parse_datetime(row['created_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None
            ))
        
        return relationships
    
    def delete_relationship(self, relationship_id: str) -> bool:
        """
        Soft-delete a relationship.
        
        Args:
            relationship_id: Relationship ID to delete
            
        Returns:
            True if successful
        """
        try:
            self.conn.execute("""
                UPDATE relationships
                SET deleted_at = ?
                WHERE id = ?
            """, (datetime.utcnow(), relationship_id))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    # ========== Event Operations ==========
    
    def log_event(self, event: Event) -> None:
        """
        Log an event to the database.
        
        Args:
            event: Event to log
        """
        self.conn.execute("""
            INSERT INTO events
            (event_id, timestamp, event_type, entity_id, component_id, actor_id, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.timestamp,
            event.event_type,
            event.entity_id,
            event.component_id,
            event.actor_id,
            json.dumps(event.data)
        ))
        self.conn.commit()
    
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
        query = "SELECT event_id, timestamp, event_type, entity_id, component_id, actor_id, data FROM events"
        params = []
        where_clauses = []
        
        if entity_id:
            where_clauses.append("entity_id = ?")
            params.append(entity_id)
        
        if event_type:
            where_clauses.append("event_type = ?")
            params.append(event_type)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            events.append(Event(
                event_id=row['event_id'],
                timestamp=self._parse_datetime(row['timestamp']),
                event_type=row['event_type'],
                entity_id=row['entity_id'],
                component_id=row['component_id'],
                actor_id=row['actor_id'],
                data=json.loads(row['data'])
            ))
        
        return events
    
    # ========== Query Operations ==========
    
    def query_entities(self, component_types: Optional[List[str]] = None) -> List[Entity]:
        """
        Query entities that have specific component types.
        
        Args:
            component_types: List of component types that entities must have
                           If None, returns all entities
            
        Returns:
            List of entities matching the query
        """
        if not component_types:
            return self.list_entities()
        
        # Build query to find entities with all specified component types
        placeholders = ','.join('?' * len(component_types))
        query = f"""
            SELECT DISTINCT e.id, e.name, e.created_at, e.modified_at, e.deleted_at, e.deleted_by
            FROM entities e
            WHERE e.deleted_at IS NULL
            AND (
                SELECT COUNT(DISTINCT c.component_type)
                FROM components c
                WHERE c.entity_id = e.id
                AND c.component_type IN ({placeholders})
                AND c.deleted_at IS NULL
            ) = ?
            ORDER BY e.name
        """
        
        params = component_types + [len(component_types)]
        cursor = self.conn.execute(query, params)
        
        entities = []
        for row in cursor.fetchall():
            entities.append(Entity(
                id=row['id'],
                name=row['name'],
                created_at=self._parse_datetime(row['created_at']),
                modified_at=self._parse_datetime(row['modified_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None,
                deleted_by=row['deleted_by']
            ))
        
        return entities
    
    def search_text(self, query: str) -> List[Entity]:
        """
        Full-text search across component data.
        
        Args:
            query: Search query string
            
        Returns:
            List of entities with components matching the search
        """
        cursor = self.conn.execute("""
            SELECT DISTINCT e.id, e.name, e.created_at, e.modified_at, e.deleted_at, e.deleted_by
            FROM entities e
            JOIN components_fts fts ON e.id = fts.entity_id
            WHERE components_fts MATCH ?
            AND e.deleted_at IS NULL
            ORDER BY e.name
        """, (query,))
        
        entities = []
        for row in cursor.fetchall():
            entities.append(Entity(
                id=row['id'],
                name=row['name'],
                created_at=self._parse_datetime(row['created_at']),
                modified_at=self._parse_datetime(row['modified_at']),
                deleted_at=self._parse_datetime(row['deleted_at']) if row['deleted_at'] else None,
                deleted_by=row['deleted_by']
            ))
        
        return entities
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def _parse_datetime(dt_string: str) -> datetime:
        """
        Parse datetime string from database.
        
        Args:
            dt_string: ISO format datetime string
            
        Returns:
            Datetime object
        """
        if isinstance(dt_string, datetime):
            return dt_string
        return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
