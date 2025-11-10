# Arcane Arsenal - Project Plan

## Project Overview

**Arcane Arsenal** is a roleplaying state manager built on Entity Component System (ECS) architecture. Its purpose is to maintain the best possible representation of digital RPG worlds in a way that prevents AI hallucination and enables versatile usage patterns.

### Core Goals

1. **Stateful World Representation**: Hold entities (characters, locations, items) with their components in a persistent, queryable format
2. **AI-Friendly**: Strict typing and explicit relationships prevent hallucination
3. **Modular**: Modules can add new component types, relationship types, and game systems
4. **Network-Ready**: Event-driven architecture supports multiplayer from the ground up

### Key Design Principles

- **Composition over Inheritance**: ECS pattern allows flexible entity composition
- **Explicit over Implicit**: All relationships and types are explicitly defined
- **Validation in Code, Not Database**: DB stores data and enforces foreign keys; business logic lives in Python
- **Event-Driven**: All state changes emit events for audit trails and network sync

---

## Architecture

### Layered Design

```
┌─────────────────────────────────────────┐
│  Web UI / CLI / API                     │  Consumer layer
├─────────────────────────────────────────┤
│  Modules                                │  Game logic & domain types
│  - Component definitions                │
│  - Relationship definitions             │
│  - Validation logic                     │
├─────────────────────────────────────────┤
│  Core Engine                            │  State management
│  - StateEngine (CRUD, queries)          │
│  - Event Bus (pub/sub)                  │
│  - AI context generation                │
├─────────────────────────────────────────┤
│  Storage Layer                          │  Persistence
│  - SQLite database                      │
│  - Query builder                        │
│  - Transaction management               │
└─────────────────────────────────────────┘
```

### Entity Component System (ECS)

**Entity**: Just an ID with a name. All data comes from components.

**Component**: Typed data container attached to an entity.
- Examples: Identity, Health, Position, Inventory, DnD5eStats

**Relationship**: Explicit connection between two entities.
- Examples: located_at, knows, contains, equipped_by

**System**: Logic that queries entities by their components and performs operations.

---

## Database Schema

### Core Philosophy
- Registries enforce type safety (component_types, relationship_types, event_types)
- Foreign keys prevent invalid references
- JSON stores flexible data within typed containers
- Soft deletes preserve history

### Complete SQL Schema

```sql
-- ============= TYPE REGISTRIES =============
-- Modules register their types here before use

CREATE TABLE component_types (
    type TEXT PRIMARY KEY,
    description TEXT,
    schema_version TEXT NOT NULL,
    module TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE relationship_types (
    type TEXT PRIMARY KEY,
    description TEXT,
    module TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE event_types (
    type TEXT PRIMARY KEY,
    description TEXT,
    module TEXT,
    created_at TIMESTAMP NOT NULL
);

-- ============= DATA TABLES =============

-- Entities: Minimal metadata, all real data in components
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    deleted_by TEXT  -- entity_id or 'system'
);

-- Components: All entity data lives here
CREATE TABLE components (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    component_type TEXT NOT NULL,
    data JSON NOT NULL,
    version INTEGER DEFAULT 1,  -- Increments on each update
    created_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (component_type) REFERENCES component_types(type)
);

-- Relationships: Explicit connections between entities
CREATE TABLE relationships (
    id TEXT PRIMARY KEY,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    FOREIGN KEY (from_entity) REFERENCES entities(id),
    FOREIGN KEY (to_entity) REFERENCES entities(id),
    FOREIGN KEY (relationship_type) REFERENCES relationship_types(type)
);

-- Events: Append-only audit log
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    event_type TEXT NOT NULL,
    entity_id TEXT,
    component_id TEXT,
    actor_id TEXT,  -- Who caused this event
    data JSON NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (event_type) REFERENCES event_types(type)
);

-- ============= INDEXES =============

-- Entity indexes
CREATE INDEX idx_entities_active ON entities(name) WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_deleted ON entities(deleted_at) WHERE deleted_at IS NOT NULL;

-- Component indexes
CREATE INDEX idx_components_entity ON components(entity_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_components_type ON components(component_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_components_entity_type ON components(entity_id, component_type) WHERE deleted_at IS NULL;

-- Relationship indexes
CREATE INDEX idx_relationships_from ON relationships(from_entity, relationship_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_to ON relationships(to_entity, relationship_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_type ON relationships(relationship_type) WHERE deleted_at IS NULL;

-- Event indexes
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_entity ON events(entity_id);
CREATE INDEX idx_events_actor ON events(actor_id);
CREATE INDEX idx_events_type ON events(event_type);

-- ============= FULL-TEXT SEARCH =============

-- For AI natural language queries
CREATE VIRTUAL TABLE components_fts USING fts5(
    id UNINDEXED,
    entity_id UNINDEXED,
    component_type UNINDEXED,
    data
);

-- Triggers to keep FTS in sync
CREATE TRIGGER components_fts_insert AFTER INSERT ON components BEGIN
    INSERT INTO components_fts(rowid, id, entity_id, component_type, data)
    VALUES (new.rowid, new.id, new.entity_id, new.component_type, new.data);
END;

CREATE TRIGGER components_fts_delete AFTER DELETE ON components BEGIN
    DELETE FROM components_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER components_fts_update AFTER UPDATE ON components BEGIN
    DELETE FROM components_fts WHERE rowid = old.rowid;
    INSERT INTO components_fts(rowid, id, entity_id, component_type, data)
    VALUES (new.rowid, new.id, new.entity_id, new.component_type, new.data);
END;
```

---

## Project Structure

```
arcane-arsenal/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py           # Entity, Component, Event, Relationship classes
│   │   ├── result.py           # Result object for error handling
│   │   ├── storage.py          # SQLite interface
│   │   ├── state_engine.py     # Main API
│   │   ├── event_bus.py        # Event system
│   │   └── query.py            # Query builder
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base.py             # Module interface
│   │   └── core_components/    # Basic component types
│   │       ├── __init__.py
│   │       ├── identity.py     # Identity component
│   │       └── position.py     # Position component
│   ├── web/
│   │   ├── __init__.py
│   │   ├── server.py           # Flask app
│   │   ├── static/
│   │   │   └── style.css
│   │   └── templates/
│   │       ├── index.html      # Entity list
│   │       ├── entity.html     # Entity detail
│   │       └── events.html     # Event log viewer
│   └── cli/
│       ├── __init__.py
│       └── commands.py         # CLI for testing
├── tests/
│   ├── unit/
│   │   ├── test_storage.py
│   │   ├── test_events.py
│   │   ├── test_state_engine.py
│   │   └── test_validation.py
│   ├── integration/
│   │   └── test_workflows.py
│   └── fixtures/
│       └── sample_data.py
├── worlds/                     # User world data stored here
│   └── .gitkeep
├── docs/
│   ├── architecture.md
│   ├── ai_integration.md
│   └── module_guide.md
├── schema.sql                  # Complete DB schema
├── requirements.txt
├── setup.py
├── README.md
└── PROJECT_PLAN.md            # This file
```

---

## Core Data Models

### Entity Model
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Entity:
    id: str
    name: str
    created_at: datetime
    modified_at: datetime
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
```

### Component Model
```python
@dataclass
class Component:
    id: str
    entity_id: str
    component_type: str
    data: dict
    version: int
    created_at: datetime
    modified_at: datetime
    deleted_at: Optional[datetime] = None
```

### Relationship Model
```python
@dataclass
class Relationship:
    id: str
    from_entity: str
    to_entity: str
    relationship_type: str
    metadata: Optional[dict] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None
```

### Event Model
```python
@dataclass
class Event:
    event_id: str
    timestamp: datetime
    event_type: str
    entity_id: Optional[str]
    component_id: Optional[str]
    actor_id: Optional[str]
    data: dict
```

### Result Object
```python
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class Result:
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    @staticmethod
    def ok(data=None) -> 'Result':
        return Result(success=True, data=data)
    
    @staticmethod
    def fail(error: str, code: str = None) -> 'Result':
        return Result(success=False, error=error, error_code=code)
```

---

## Module System

### Module Interface

```python
from abc import ABC, abstractmethod
from typing import List

class Module(ABC):
    """Base class for all modules"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Module name"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Module version (semver)"""
        pass
    
    def initialize(self, engine: 'StateEngine'):
        """Called when module is loaded"""
        pass
    
    def register_component_types(self) -> List['ComponentTypeDefinition']:
        """Return component types this module provides"""
        return []
    
    def register_relationship_types(self) -> List['RelationshipTypeDefinition']:
        """Return relationship types this module provides"""
        return []
    
    def register_event_types(self) -> List['EventTypeDefinition']:
        """Return event types this module provides"""
        return []
    
    def on_event(self, event: Event):
        """Optional: React to events"""
        pass
```

### Type Definitions

```python
from abc import ABC, abstractmethod

class ComponentTypeDefinition(ABC):
    """Defines a component type with validation"""
    
    type: str
    description: str
    schema_version: str
    
    @abstractmethod
    def get_schema(self) -> dict:
        """Return JSON Schema for validation"""
        pass
    
    def validate(self, data: dict) -> bool:
        """Validate component data against schema"""
        import jsonschema
        jsonschema.validate(data, self.get_schema())
        return True

class RelationshipTypeDefinition(ABC):
    """Defines a relationship type with validation"""
    
    type: str
    description: str
    
    def validate_from_entity(self, entity: Entity) -> bool:
        """Override to validate from_entity has required components"""
        return True
    
    def validate_to_entity(self, entity: Entity) -> bool:
        """Override to validate to_entity has required components"""
        return True

class EventTypeDefinition:
    """Defines an event type"""
    
    type: str
    description: str
    data_schema: dict  # JSON Schema for event.data
```

### Example: Core Components Module

```python
# src/modules/core_components/identity.py

from ..base import ComponentTypeDefinition

class IdentityComponent(ComponentTypeDefinition):
    type = "Identity"
    description = "Basic identity information for any entity"
    schema_version = "1.0.0"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["description"]
        }

# src/modules/core_components/position.py

class PositionComponent(ComponentTypeDefinition):
    type = "Position"
    description = "Spatial position in the world"
    schema_version = "1.0.0"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
                "z": {"type": "number"},
                "region": {"type": "string"}
            }
        }
```

---

## AI Context Format

AI receives structured context to prevent hallucination. All data is explicit and queryable.

### AI Context Structure

```python
{
    "focus_entity": {
        "id": "char_theron",
        "name": "Theron",
        "components": {
            "Identity": {
                "description": "A brave warrior",
                "tags": ["player", "human"]
            },
            "Health": {
                "current": 25,
                "max": 30
            },
            "Position": {
                "x": 100,
                "y": 200,
                "region": "tavern"
            }
        }
    },
    "nearby_entities": [
        {
            "id": "char_elara",
            "name": "Elara",
            "distance": 5,
            "components": {...}
        }
    ],
    "relationships": [
        {
            "from": "char_theron",
            "to": "loc_tavern",
            "type": "located_at",
            "metadata": {"since": "2024-03-15"}
        },
        {
            "from": "char_theron",
            "to": "char_elara",
            "type": "knows",
            "metadata": {"trust_level": 8}
        }
    ],
    "recent_events": [
        {
            "event_id": "evt_001",
            "type": "character.moved",
            "timestamp": "2024-03-15T10:00:00Z",
            "data": {...}
        }
    ],
    "available_actions": [
        {
            "action": "move",
            "description": "Move to a different location",
            "targets": ["loc_forest", "loc_market"],
            "requirements_met": true
        },
        {
            "action": "interact",
            "description": "Interact with a character",
            "targets": ["char_elara"],
            "requirements_met": true
        }
    ]
}
```

### Querying for AI Context

```python
def get_ai_context(engine: StateEngine, focus_entity_id: str) -> dict:
    """Generate AI context for a specific entity"""
    
    # Get focus entity with all components
    focus = engine.get_entity(focus_entity_id)
    components = engine.get_entity_components(focus_entity_id)
    
    # Get relationships
    relationships = engine.get_entity_relationships(focus_entity_id)
    
    # Get nearby entities (if Position component exists)
    nearby = []
    if "Position" in components:
        nearby = engine.query_nearby_entities(focus_entity_id, radius=50)
    
    # Get recent events involving this entity
    recent_events = engine.get_entity_events(focus_entity_id, limit=10)
    
    # Generate available actions based on components and context
    actions = generate_available_actions(focus, components, relationships)
    
    return {
        "focus_entity": {
            "id": focus.id,
            "name": focus.name,
            "components": components
        },
        "nearby_entities": nearby,
        "relationships": relationships,
        "recent_events": recent_events,
        "available_actions": actions
    }
```

---

## State Engine API

### Core Operations

```python
class StateEngine:
    """Main interface for world state management"""
    
    def __init__(self, world_path: str):
        """Initialize engine for a world"""
        pass
    
    # ===== Entity Operations =====
    
    def create_entity(self, name: str) -> Result:
        """Create a new entity"""
        pass
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve entity by ID"""
        pass
    
    def update_entity(self, entity_id: str, name: str) -> Result:
        """Update entity name"""
        pass
    
    def delete_entity(self, entity_id: str, actor_id: str = 'system') -> Result:
        """Soft-delete an entity"""
        pass
    
    def restore_entity(self, entity_id: str) -> Result:
        """Restore a soft-deleted entity"""
        pass
    
    # ===== Component Operations =====
    
    def add_component(self, entity_id: str, component_type: str, data: dict) -> Result:
        """Add a component to an entity"""
        pass
    
    def get_component(self, entity_id: str, component_type: str) -> Optional[Component]:
        """Get a specific component from an entity"""
        pass
    
    def get_entity_components(self, entity_id: str) -> dict:
        """Get all components for an entity as {type: data}"""
        pass
    
    def update_component(self, entity_id: str, component_type: str, data: dict) -> Result:
        """Update component data"""
        pass
    
    def remove_component(self, entity_id: str, component_type: str) -> Result:
        """Remove a component from an entity"""
        pass
    
    # ===== Relationship Operations =====
    
    def create_relationship(self, from_id: str, to_id: str, 
                          rel_type: str, metadata: dict = None) -> Result:
        """Create a relationship between entities"""
        pass
    
    def get_relationships(self, entity_id: str, 
                         rel_type: str = None, 
                         direction: str = 'both') -> List[Relationship]:
        """Get relationships for an entity
        
        Args:
            direction: 'from', 'to', or 'both'
        """
        pass
    
    def delete_relationship(self, relationship_id: str) -> Result:
        """Delete a relationship"""
        pass
    
    # ===== Query Operations =====
    
    def query_entities(self, 
                      component_types: List[str] = None,
                      filters: dict = None) -> List[Entity]:
        """Query entities by components and filters"""
        pass
    
    def search_text(self, query: str) -> List[Entity]:
        """Full-text search across component data"""
        pass
    
    # ===== Event Operations =====
    
    def get_events(self, 
                  entity_id: str = None,
                  event_type: str = None,
                  limit: int = 100) -> List[Event]:
        """Retrieve event history"""
        pass
    
    # ===== AI Integration =====
    
    def get_ai_context(self, focus_entity_id: str) -> dict:
        """Generate structured context for AI"""
        pass
    
    # ===== Type Registration =====
    
    def register_component_type(self, definition: ComponentTypeDefinition) -> Result:
        """Register a new component type"""
        pass
    
    def register_relationship_type(self, definition: RelationshipTypeDefinition) -> Result:
        """Register a new relationship type"""
        pass
    
    def register_event_type(self, definition: EventTypeDefinition) -> Result:
        """Register a new event type"""
        pass
    
    # ===== Transaction Support =====
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        pass
```

---

## Phase 1: Core Foundation

### Implementation Order

1. **Project Setup**
   - Create directory structure
   - Set up requirements.txt (Flask, pytest, jsonschema)
   - Create schema.sql file

2. **Core Models** (`src/core/models.py`, `src/core/result.py`)
   - Entity, Component, Relationship, Event dataclasses
   - Result object for error handling

3. **Storage Layer** (`src/core/storage.py`)
   - WorldStorage class
   - Database initialization
   - CRUD operations for all tables
   - Transaction support
   - Query builder

4. **Event System** (`src/core/event_bus.py`)
   - EventBus class
   - Pub/sub pattern
   - Event logging

5. **State Engine** (`src/core/state_engine.py`)
   - Implement all StateEngine methods
   - Validation logic
   - Transaction wrappers

6. **Core Components Module** (`src/modules/core_components/`)
   - Identity component
   - Position component
   - Register on world init

7. **CLI Tool** (`src/cli/commands.py`)
   - Initialize world
   - Create/list/delete entities
   - Add/list components
   - Create relationships
   - View events

8. **Web Viewer** (`src/web/server.py`)
   - Flask app
   - Routes: /, /entities, /entity/<id>, /events
   - Simple HTML templates
   - Read-only viewing

9. **Tests**
   - Unit tests for each component
   - Integration tests for workflows
   - Test fixtures

### Success Criteria

Phase 1 is complete when:
- ✅ Can create a new world
- ✅ Can create entities with components
- ✅ Can create relationships between entities
- ✅ All changes are logged as events
- ✅ Can query entities by component type
- ✅ Can view state in web browser
- ✅ All tests pass
- ✅ Core module with Identity and Position components works

---

## Technical Stack

### Core Dependencies
- **Python**: 3.11+
- **SQLite**: 3.35+ (built-in)
- **Flask**: Web server for state viewer
- **Pydantic** or **dataclasses**: Data validation
- **jsonschema**: Component schema validation
- **pytest**: Testing

### Development Tools
- **mypy**: Type checking
- **black**: Code formatting
- **pylint**: Linting

---

## World Initialization

### Initialization Sequence

```python
def initialize_world(world_path: str, world_name: str):
    """Initialize a new world"""
    
    # 1. Create directory structure
    os.makedirs(f"{world_path}", exist_ok=True)
    
    # 2. Create SQLite database
    db_path = f"{world_path}/world.db"
    
    # 3. Run schema SQL
    with open("schema.sql") as f:
        schema = f.read()
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.commit()
    
    # 4. Create 'system' entity
    system_entity = Entity(
        id="system",
        name="System",
        created_at=datetime.utcnow(),
        modified_at=datetime.utcnow()
    )
    storage.save_entity(system_entity)
    
    # 5. Load core module
    core_module = CoreComponentsModule()
    
    # 6. Register core types
    for comp_type in core_module.register_component_types():
        storage.register_component_type(comp_type)
    
    for rel_type in core_module.register_relationship_types():
        storage.register_relationship_type(rel_type)
    
    # 7. Emit world.created event
    event = Event(
        event_id=generate_id("evt"),
        timestamp=datetime.utcnow(),
        event_type="world.created",
        entity_id=None,
        component_id=None,
        actor_id="system",
        data={"world_name": world_name}
    )
    storage.log_event(event)
```

---

## Next Steps: Character Manager Module (Phase 2)

After Phase 1 is complete, we'll build on this foundation:

### Character Manager Features
- Health component (current/max HP)
- Stats component (game-system specific)
- Inventory component (list of item entity IDs)
- Character sheet export
- Level up operations
- AI-friendly character context

### Character-Specific Relationships
- `owns` (character owns item)
- `equipped_in` (item equipped in slot)
- `member_of` (character in party/faction)

---

## Design Decisions Log

### Why ECS over traditional OOP?
- Maximum flexibility for diverse game systems
- Clear data/logic separation
- Modules can add components without modifying core
- AI gets explicit, typed data

### Why SQLite over PostgreSQL?
- Single-file portability
- No server setup required
- Good enough performance for RPG state
- Full-text search built-in
- Can migrate to Postgres later if needed

### Why soft deletes?
- Preserve history and audit trails
- Support undo operations
- Keep referential integrity
- Can query "deleted" state for recovery

### Why JSON in components?
- Game systems vary wildly
- Schema validation in code is flexible
- SQLite JSON functions are powerful
- Easy to extend without migrations

### Why separate relationship types registry?
- Prevents AI hallucination ("contains" vs "has" vs "inside")
- Self-documenting for AI
- Enables validation logic per type
- Clear error messages guide correct usage

---

## Contact & Contribution

This is a personal project by Samuel. For questions or contributions, reach out through the project repository.

---

**Project Status**: Phase 1 - Core Foundation (COMPLETE ✅)
**Last Updated**: 2025-11-06
