# Claude Code Implementation Guide

This guide provides Claude Code with the implementation order and current project status.

## Current Status

✅ **Completed:**
- Project directory structure created
- PROJECT_PLAN.md with complete architecture
- schema.sql with full database schema
- requirements.txt with dependencies
- README.md with overview

❌ **Not Yet Started:**
- Core Python modules
- Tests
- CLI tool
- Web viewer

## Implementation Order

Follow this exact order for Phase 1 implementation:

### Step 1: Core Models (`src/core/`)

Create these files in order:

1. **`src/core/result.py`**
   - Result dataclass for error handling
   - See PROJECT_PLAN.md section "Core Data Models > Result Object"

2. **`src/core/models.py`**
   - Entity, Component, Relationship, Event dataclasses
   - Helper functions for ID generation
   - See PROJECT_PLAN.md section "Core Data Models"

### Step 2: Storage Layer (`src/core/storage.py`)

1. **WorldStorage class**
   - Database connection management
   - Initialize database with schema.sql
   - CRUD operations for all tables
   - Transaction support (begin, commit, rollback)
   - Query builder methods

Key methods to implement:
```python
class WorldStorage:
    def __init__(self, db_path: str)
    def initialize(self)
    def begin_transaction(self)
    def commit(self)
    def rollback(self)
    
    # Type registry methods
    def register_component_type(self, type_name, description, schema_version, module)
    def register_relationship_type(self, type_name, description, module)
    def register_event_type(self, type_name, description, module)
    def get_component_types(self) -> List[dict]
    def get_relationship_types(self) -> List[dict]
    
    # Entity CRUD
    def save_entity(self, entity: Entity) -> bool
    def get_entity(self, entity_id: str) -> Optional[Entity]
    def list_entities(self, include_deleted: bool = False) -> List[Entity]
    def soft_delete_entity(self, entity_id: str, deleted_by: str)
    def restore_entity(self, entity_id: str)
    
    # Component CRUD
    def save_component(self, component: Component) -> bool
    def get_component(self, entity_id: str, component_type: str) -> Optional[Component]
    def get_entity_components(self, entity_id: str) -> List[Component]
    def list_components_by_type(self, component_type: str) -> List[Component]
    def delete_component(self, component_id: str)
    
    # Relationship CRUD
    def save_relationship(self, relationship: Relationship) -> bool
    def get_relationship(self, relationship_id: str) -> Optional[Relationship]
    def get_entity_relationships(self, entity_id: str, direction: str = 'both') -> List[Relationship]
    def delete_relationship(self, relationship_id: str)
    
    # Event logging
    def log_event(self, event: Event)
    def get_events(self, entity_id=None, event_type=None, limit=100) -> List[Event]
    
    # Queries
    def query_entities(self, component_types: List[str] = None) -> List[Entity]
    def search_text(self, query: str) -> List[Entity]
```

### Step 3: Event System (`src/core/event_bus.py`)

1. **EventBus class**
   - Pub/sub pattern for events
   - Event logging via WorldStorage
   - Listener management

```python
class EventBus:
    def __init__(self, storage: WorldStorage)
    def subscribe(self, event_type: str, callback: Callable)
    def unsubscribe(self, event_type: str, callback: Callable)
    def publish(self, event: Event)
```

### Step 4: State Engine (`src/core/state_engine.py`)

This is the main API. Implements all methods from PROJECT_PLAN.md section "State Engine API".

Key responsibilities:
- Use WorldStorage for persistence
- Use EventBus for change notifications
- Validate all operations
- Emit events for all state changes
- Provide transaction support

Critical methods:
```python
class StateEngine:
    def __init__(self, world_path: str)
    
    # Entity operations
    def create_entity(self, name: str, actor_id: str = 'system') -> Result
    def get_entity(self, entity_id: str) -> Optional[Entity]
    def update_entity(self, entity_id: str, name: str, actor_id: str = 'system') -> Result
    def delete_entity(self, entity_id: str, actor_id: str = 'system') -> Result
    
    # Component operations
    def add_component(self, entity_id: str, component_type: str, data: dict, actor_id: str = 'system') -> Result
    def get_component(self, entity_id: str, component_type: str) -> Optional[Component]
    def update_component(self, entity_id: str, component_type: str, data: dict, actor_id: str = 'system') -> Result
    def remove_component(self, entity_id: str, component_type: str, actor_id: str = 'system') -> Result
    
    # Relationship operations
    def create_relationship(self, from_id: str, to_id: str, rel_type: str, metadata: dict = None, actor_id: str = 'system') -> Result
    def get_relationships(self, entity_id: str, rel_type: str = None, direction: str = 'both') -> List[Relationship]
    def delete_relationship(self, relationship_id: str, actor_id: str = 'system') -> Result
    
    # Type registration
    def register_component_type(self, definition: ComponentTypeDefinition) -> Result
    def register_relationship_type(self, definition: RelationshipTypeDefinition) -> Result
    
    # Transactions
    @contextmanager
    def transaction(self)
```

### Step 5: Module System (`src/modules/base.py`)

1. **Base Module classes**
   - Module interface (abstract base class)
   - ComponentTypeDefinition
   - RelationshipTypeDefinition
   - EventTypeDefinition

See PROJECT_PLAN.md section "Module System" for complete class definitions.

### Step 6: Core Components Module (`src/modules/core_components/`)

Create basic components that ship with core:

1. **`identity.py`** - IdentityComponent
   - Schema: {description: string, tags: [string]}

2. **`position.py`** - PositionComponent
   - Schema: {x: number, y: number, z: number, region: string}

Also create relationship types in `__init__.py`:
- `located_at`: Entity is physically at a location
- `contains`: Entity contains another entity

### Step 7: World Initialization

Add to StateEngine:
```python
@staticmethod
def initialize_world(world_path: str, world_name: str) -> StateEngine:
    """Create a new world and return initialized engine"""
    # Create directory
    # Create database with schema
    # Create 'system' entity
    # Load and register core components module
    # Emit world.created event
    # Return StateEngine instance
```

### Step 8: CLI Tool (`src/cli/commands.py`)

Command-line interface for testing. Use `argparse` or `click`.

Commands to implement:
```bash
# Initialize new world
python -m src.cli.commands init <world_path> [--name <world_name>]

# Entity operations
python -m src.cli.commands entity create <world_path> <entity_name>
python -m src.cli.commands entity list <world_path>
python -m src.cli.commands entity get <world_path> <entity_id>
python -m src.cli.commands entity delete <world_path> <entity_id>

# Component operations
python -m src.cli.commands component add <world_path> <entity_id> <component_type> <json_data>
python -m src.cli.commands component list <world_path> <entity_id>
python -m src.cli.commands component get <world_path> <entity_id> <component_type>

# Relationship operations
python -m src.cli.commands relationship create <world_path> <from_id> <to_id> <rel_type>
python -m src.cli.commands relationship list <world_path> <entity_id>

# Event viewing
python -m src.cli.commands events <world_path> [--entity <entity_id>] [--type <event_type>]

# Type registry viewing
python -m src.cli.commands types components <world_path>
python -m src.cli.commands types relationships <world_path>
```

### Step 9: Web Viewer (`src/web/`)

Simple Flask app for viewing state in browser.

1. **`src/web/server.py`**

Routes:
```python
@app.route('/')
def index() -> "List all entities"

@app.route('/entity/<entity_id>')
def entity_detail(entity_id) -> "Show entity with all components and relationships"

@app.route('/events')
def events() -> "Show recent events"

@app.route('/api/entities')
def api_entities() -> "JSON: list entities"

@app.route('/api/entity/<entity_id>')
def api_entity(entity_id) -> "JSON: entity details"

@app.route('/api/events')
def api_events() -> "JSON: recent events"
```

2. **Templates** (`src/web/templates/`)
   - `index.html` - Entity list page
   - `entity.html` - Entity detail page
   - `events.html` - Event log page

3. **Static files** (`src/web/static/`)
   - `style.css` - Basic styling

Keep it simple - focus on functionality, not design.

### Step 10: Tests

Create tests for each component:

1. **`tests/unit/test_storage.py`**
   - Test all WorldStorage CRUD operations
   - Test transactions
   - Test queries

2. **`tests/unit/test_events.py`**
   - Test EventBus pub/sub
   - Test event logging

3. **`tests/unit/test_state_engine.py`**
   - Test StateEngine operations
   - Test validation
   - Test error handling

4. **`tests/integration/test_workflows.py`**
   - Test complete workflows (create entity → add components → create relationships)
   - Test world initialization

5. **`tests/fixtures/sample_data.py`**
   - Helper functions to create test data

Use pytest fixtures for setup/teardown.

## Testing Strategy

After each major component is implemented, write tests before moving to the next step. This ensures everything works before building on top of it.

Example test flow:
```python
# tests/unit/test_storage.py
def test_create_entity():
    storage = WorldStorage(":memory:")
    storage.initialize()
    
    entity = Entity(
        id="test_001",
        name="Test Entity",
        created_at=datetime.utcnow(),
        modified_at=datetime.utcnow()
    )
    
    assert storage.save_entity(entity) == True
    retrieved = storage.get_entity("test_001")
    assert retrieved.name == "Test Entity"
```

## Code Style Guidelines

- Use type hints everywhere
- Docstrings for all public methods
- Keep functions small and focused
- Return Result objects for operations that can fail
- Use context managers for transactions
- Validate inputs early

## Common Patterns

### ID Generation
```python
import uuid

def generate_id(prefix: str) -> str:
    """Generate unique ID with prefix"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
```

### Error Handling
```python
# Always return Result
def risky_operation() -> Result:
    try:
        # do work
        return Result.ok(data)
    except Exception as e:
        return Result.fail(str(e), "ERROR_CODE")

# Caller checks success
result = risky_operation()
if not result.success:
    print(f"Error: {result.error}")
    return
# use result.data
```

### Validation Pattern
```python
def add_component(self, entity_id: str, component_type: str, data: dict) -> Result:
    # 1. Check entity exists
    entity = self.storage.get_entity(entity_id)
    if not entity:
        return Result.fail(f"Entity {entity_id} not found", "ENTITY_NOT_FOUND")
    
    # 2. Check type is registered
    if component_type not in self.component_validators:
        return Result.fail(f"Component type {component_type} not registered", "TYPE_NOT_REGISTERED")
    
    # 3. Validate data against schema
    try:
        self.component_validators[component_type].validate(data)
    except ValidationError as e:
        return Result.fail(f"Validation failed: {e}", "VALIDATION_ERROR")
    
    # 4. Perform operation
    # 5. Emit event
    # 6. Return success
```

## Success Criteria

Phase 1 is complete when:
- [ ] All core classes implemented and tested
- [ ] Can initialize a world via CLI
- [ ] Can create entities with components via CLI
- [ ] Can create relationships via CLI
- [ ] All changes logged as events
- [ ] Web viewer displays entities, components, relationships, events
- [ ] All tests pass
- [ ] Core components module (Identity, Position) works

## Implementation Tips

1. **Start simple**: Get basic CRUD working before adding fancy features
2. **Test as you go**: Write tests immediately after implementing each component
3. **Use the CLI**: Test your work with the CLI tool before building the web viewer
4. **Check PROJECT_PLAN.md**: All detailed specifications are there
5. **Follow the order**: Each step builds on the previous one

## Next Phase Preview

After Phase 1 works, we'll build:
- **Character Manager Module**: Health, Stats, Inventory components
- **AI Context Generation**: Structured output for LLMs
- **Advanced Queries**: Component-based entity queries
- **Networking Layer**: WebSocket for multiplayer

But focus on Phase 1 first!

---

**Ready to start?** Begin with `src/core/result.py` and work through the steps in order.
