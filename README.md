# Arcane Arsenal

A complete **Entity Component System (ECS)** roleplaying state manager designed to prevent AI hallucination and enable versatile RPG world management.

## ✨ What's New

**Phase 1 Complete!** Arcane Arsenal now features:
- ✅ **Full Web Interface** - Create, edit, and delete entities, components, and relationships from your browser
- ✅ **CLI Tools** - Complete command-line interface for scripting and automation
- ✅ **Event Tracking** - Complete audit trail of all state changes
- ✅ **JSON API** - RESTful endpoints for programmatic access
- ✅ **46 Tests** - Comprehensive test suite (100% passing)

## Overview

Arcane Arsenal provides:
- **Flexible Entity Composition**: Build any game object from reusable components
- **AI-Friendly State**: Explicit, structured data prevents LLM hallucination
- **Modular Architecture**: Add new game systems without touching core
- **Event-Driven**: Complete audit trail and network-ready from day one
- **Web Editor**: Full CRUD operations with beautiful, user-friendly interface

## Quick Start

### Installation

```bash
# Install dependencies
pip install flask jsonschema pytest

# Or use requirements.txt
pip install -r requirements.txt
```

### Create Your First World

```bash
# Initialize a new world
python -m src.cli.commands init worlds/my_world --name "My World"

# Create an entity
python -m src.cli.commands entity create worlds/my_world "Hero"

# Add a component
python -m src.cli.commands component add worlds/my_world <entity_id> Identity \
  '{"description": "A brave adventurer"}'
```

### Start the Web Interface

```bash
python src/web/server.py worlds/my_world
```

Visit **http://localhost:5000** to:
- ✅ Create entities with the click of a button
- ✅ Add and edit components with JSON validation
- ✅ Create relationships between entities
- ✅ View complete event history
- ✅ Delete and manage everything visually

See **[WEB_EDITING_GUIDE.md](WEB_EDITING_GUIDE.md)** for detailed instructions.

## Architecture

```
Entity (ID + Name)
  └─> Components (typed data containers)
      └─> Identity: description
      └─> Position: x, y, z, region
  └─> Relationships (explicit connections)
      └─> located_at: entity → location
      └─> contains: container → entity
  └─> Events (immutable audit log)
```

All state changes emit **Events** for complete traceability.

## Core Features

### 1. Entity Component System

```python
from src.core.state_engine import StateEngine

# Initialize or open a world
engine = StateEngine.initialize_world('worlds/my_world', 'My World')

# Create entities
result = engine.create_entity('Theron the Brave')
entity_id = result.data['id']

# Add components
engine.add_component(entity_id, 'Identity', {
    'description': 'A brave warrior'
})

engine.add_component(entity_id, 'Position', {
    'x': 100,
    'y': 200,
    'region': 'tavern'
})

# Create relationships
engine.create_relationship(char_id, tavern_id, 'located_at')

# Query entities
entities_with_position = engine.query_entities(['Position'])
```

### 2. Web Interface

**Full CRUD Operations:**
- Create entities with forms
- Add/edit/delete components with JSON editor
- Create/delete relationships between entities
- View event history
- Flash messages for instant feedback
- Inline editing with confirmation dialogs

### 3. CLI Tool

```bash
# Entity operations
python -m src.cli.commands entity create <world> <name>
python -m src.cli.commands entity list <world>
python -m src.cli.commands entity get <world> <id>
python -m src.cli.commands entity delete <world> <id>

# Component operations
python -m src.cli.commands component add <world> <entity_id> <type> <json>
python -m src.cli.commands component list <world> <entity_id>
python -m src.cli.commands component get <world> <entity_id> <type>

# Relationship operations
python -m src.cli.commands relationship create <world> <from> <to> <type>
python -m src.cli.commands relationship list <world> <entity_id>

# Event log
python -m src.cli.commands events <world> --entity <id> --type <type>

# Type registry
python -m src.cli.commands types components <world>
python -m src.cli.commands types relationships <world>
```

### 4. JSON API

```python
GET  /api/entities              # List all entities
GET  /api/entity/<id>           # Get entity details
GET  /api/events                # Get event log
GET  /api/types                 # Get registered types
```

## Project Structure

```
arcane-arsenal/
├── src/
│   ├── core/
│   │   ├── models.py          # Entity, Component, Relationship, Event
│   │   ├── result.py          # Error handling
│   │   ├── storage.py         # SQLite storage layer
│   │   ├── event_bus.py       # Event system
│   │   └── state_engine.py    # Main API
│   ├── modules/
│   │   ├── base.py            # Module interface
│   │   └── core_components/   # Identity & Position components
│   ├── web/
│   │   ├── server.py          # Flask app with CRUD
│   │   ├── templates/         # HTML templates
│   │   └── static/            # CSS styling
│   └── cli/
│       └── commands.py        # CLI tool
├── tests/
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── worlds/                    # User world data
├── schema.sql                 # Complete database schema
├── PROJECT_PLAN.md            # Detailed architecture
├── WEB_EDITING_GUIDE.md       # Web interface tutorial
└── IMPLEMENTATION_SUMMARY.md  # Phase 1 completion report
```

## Development Status

**✅ Phase 1: Core Foundation** (COMPLETE)
- ✅ Project structure and database schema
- ✅ Storage layer with SQLite
- ✅ State engine with validation
- ✅ Core components module (Identity, Position)
- ✅ Event system with pub/sub
- ✅ CLI tool with full operations
- ✅ Web interface with CRUD
- ✅ 46 comprehensive tests (100% passing)

See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for complete details.

## Built-in Components

### Identity
Basic identification for any entity.
```json
{
  "description": "A brave warrior"
}
```

Note: Entity type is determined by component composition (e.g., entities with CharacterStats are characters), not by tags. This prevents AI hallucination through inconsistent categorization.

### Position
Spatial positioning in the world.
```json
{
  "x": 100,
  "y": 200,
  "z": 0,
  "region": "tavern"
}
```

## Built-in Relationships

- **located_at**: Entity is physically at a location
- **contains**: Container holds another entity

## Design Principles

1. **Composition over Inheritance**: ECS pattern for maximum flexibility
2. **Explicit over Implicit**: All relationships and types are registered
3. **Validation in Code**: Database stores data, Python handles business logic
4. **Event-Driven**: All state changes are trackable and syncable
5. **Soft Deletes**: Non-destructive deletion with restoration capability

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v

# Current status: 46 tests, 100% passing
```

## Examples

### Creating a Tavern Scene

```python
from src.core.state_engine import StateEngine

engine = StateEngine.initialize_world('worlds/tavern', 'The Golden Tankard')

# Create the tavern
tavern = engine.create_entity('The Golden Tankard')
tavern_id = tavern.data['id']

engine.add_component(tavern_id, 'Identity', {
    'description': 'A cozy tavern filled with adventurers'
})

engine.add_component(tavern_id, 'Position', {
    'x': 100,
    'y': 100,
    'region': 'town_center'
})

# Create a character
hero = engine.create_entity('Theron the Brave')
hero_id = hero.data['id']

engine.add_component(hero_id, 'Identity', {
    'description': 'A brave warrior seeking adventure'
})

engine.add_component(hero_id, 'Position', {
    'x': 100,
    'y': 100,
    'region': 'town_center'
})

# Place hero at tavern
engine.create_relationship(hero_id, tavern_id, 'located_at')

# Create an item
sword = engine.create_entity('Rusty Sword')
sword_id = sword.data['id']

engine.add_component(sword_id, 'Identity', {
    'description': 'An old but serviceable weapon'
})

# Put sword in tavern
engine.create_relationship(tavern_id, sword_id, 'contains')

# Query the scene
entities_here = engine.query_entities(['Position'])
events = engine.get_events(limit=10)
```

Then open the web interface to visualize and edit!

## Documentation

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Complete architecture and design
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Phase 1 completion report
- **[WEB_EDITING_GUIDE.md](WEB_EDITING_GUIDE.md)** - Web interface tutorial
- **[CLAUDE_CODE_GUIDE.md](CLAUDE_CODE_GUIDE.md)** - Implementation guide

## Use Cases

- **RPG State Management**: Track complex game worlds
- **AI Game Masters**: Provide structured context to LLMs
- **Multiplayer Games**: Event-driven state synchronization
- **Game Development**: Rapid prototyping with ECS
- **Interactive Fiction**: Manage narrative state
- **Simulation**: Track complex entity relationships

## Future Phases

### Phase 2: Character Manager
- Health and stats components
- Inventory system
- Character sheet export

### Phase 3: AI Integration
- Context generation for LLMs
- Action validation
- Natural language queries

### Phase 4: Networking
- WebSocket support
- Multiplayer synchronization
- Remote state management

## Contributing

This is a personal project by Samuel. For questions or contributions, please reach out through the project repository.

## License

Personal project. Contact for collaboration inquiries.

---

**Status**: Phase 1 Complete ✅ | **Tests**: 46/46 Passing ✅ | **Web Interface**: Full CRUD ✅
