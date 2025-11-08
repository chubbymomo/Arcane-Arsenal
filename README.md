# Arcane Arsenal

**Entity Component System (ECS) roleplaying state manager designed to prevent AI hallucination through explicit, typed game world state.**

---

## What is Arcane Arsenal?

Arcane Arsenal is a game-agnostic RPG state management system that:
- Stores entities, components, and relationships in a queryable database
- Prevents AI hallucination through strict typing and validation
- Supports multiplayer via event-driven real-time updates
- Allows modules to add game-specific systems without modifying core

**Built for:**
- AI-powered game masters that need explicit state
- Multiplayer TTRPGs with real-time synchronization
- Complex campaign management
- Game system prototyping and experimentation

---

## Quick Start

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/arcane-arsenal.git
cd arcane-arsenal
pip install -r requirements.txt
```

### Create a World

```bash
# Initialize new world
python -m src.cli.commands init worlds/my_campaign --name "My Campaign"

# Start web interface
python src/web/server.py worlds/my_campaign
```

Visit **http://localhost:5000**:
- `/client` - Player interface (character sheets, roll dice)
- `/host` - DM interface (entity management, event log)

---

## Core Concepts

### Entity Component System

**Entity**: Unique ID with a name
- Just a container, no data of its own
- Examples: character, item, location, faction

**Component**: Typed data attached to an entity
- Defines what the entity is/has
- Examples: Health, Position, Inventory, DnD5eStats

**Relationship**: Named connection between entities
- Explicit associations
- Examples: Character --located_at--> Tavern, Character --owns--> Sword

**Event**: Immutable record of state change
- Append-only audit trail
- Examples: entity_created, health_changed, item_equipped

### State Management

```python
from src.core.state_engine import StateEngine

# Initialize or open a world
engine = StateEngine('worlds/my_campaign')

# Create entity
result = engine.create_entity('Theron the Brave')
char_id = result.data['id']

# Add components
engine.add_component(char_id, 'Identity', {
    'description': 'A brave warrior'
})

engine.add_component(char_id, 'Health', {
    'current_hp': 50,
    'max_hp': 100
})

# Create relationships
engine.create_relationship(char_id, tavern_id, 'located_at')

# Query entities
characters = engine.query_entities(['Health', 'Position'])
```

---

## Architecture

```
┌─────────────────────────────────┐
│  Web UI (Player & DM)           │
│  - Character sheets             │
│  - Real-time dice rolling       │
│  - Entity management            │
├─────────────────────────────────┤
│  Modules (Game Systems)         │
│  - D&D 5e, Pathfinder, etc.     │
│  - Component types              │
│  - Game logic systems           │
├─────────────────────────────────┤
│  Core Engine                    │
│  - StateEngine API              │
│  - Event Bus                    │
│  - Validation                   │
├─────────────────────────────────┤
│  Storage (SQLite)               │
│  - Entities, Components         │
│  - Relationships, Events        │
└─────────────────────────────────┘
```

**Technology Stack:**
- **Backend**: Python 3.11+, Flask, SQLite, Socket.IO
- **Frontend**: HTMX, Alpine.js, Socket.IO (no build step)
- **Testing**: pytest (comprehensive test suite)

---

## Documentation

### Implementation Guides (Start Here)
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Backend architectural principles
- **[FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md)** - Frontend architectural principles
- **[MODULE_GUIDE.md](MODULE_GUIDE.md)** - How to create modules

### Technical References
- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Complete schemas, APIs, data models
- **[FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)** - Frontend tutorials and examples

### Practical Guides
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Detailed setup and first steps
- **[THEMING_GUIDE.md](THEMING_GUIDE.md)** - UI theming and color system

---

## Features

### Core Modules
- **Identity**: Description and basic info
- **Position**: Spatial positioning with hierarchical regions
- **Health**: HP tracking
- **PlayerCharacter**: Player-controlled entities
- **RNG**: Dice rolling with multiplayer sync

### Web Interface
- **Player View** (`/client`):
  - Character selection and creation
  - Character sheet with live stats
  - Real-time dice rolling
  - Inventory and equipment

- **DM View** (`/host`):
  - Entity management (create, edit, delete)
  - Component editor with JSON validation
  - Relationship management
  - Event log viewer

### Real-time Features
- WebSocket-based multiplayer
- Live dice rolls broadcast to all players
- HP updates synced across clients
- Room-based event broadcasting

---

## Example: Creating a Tavern Scene

```python
from src.core.state_engine import StateEngine

engine = StateEngine('worlds/my_campaign')

# Create tavern
tavern = engine.create_entity('The Golden Tankard')
tavern_id = tavern.data['id']

engine.add_component(tavern_id, 'Identity', {
    'description': 'A cozy tavern filled with adventurers'
})

engine.add_component(tavern_id, 'Position', {
    'x': 100, 'y': 200, 'region': 'town_center'
})

# Create character
hero = engine.create_entity('Theron')
hero_id = hero.data['id']

engine.add_component(hero_id, 'Health', {
    'current_hp': 50, 'max_hp': 100
})

# Place hero at tavern
engine.create_relationship(hero_id, tavern_id, 'located_at')

# Create item in tavern
sword = engine.create_entity('Rusty Sword')
engine.create_relationship(tavern_id, sword.data['id'], 'contains')
```

Then view in web interface at http://localhost:5000/host

---

## CLI Tool

```bash
# World management
python -m src.cli.commands init <world_path> --name "World Name"

# Entity operations
python -m src.cli.commands entity create <world> "Entity Name"
python -m src.cli.commands entity list <world>
python -m src.cli.commands entity delete <world> <entity_id>

# Component operations
python -m src.cli.commands component add <world> <entity_id> <type> '<json>'
python -m src.cli.commands component list <world> <entity_id>

# Relationship operations
python -m src.cli.commands relationship create <world> <from_id> <to_id> <type>
python -m src.cli.commands relationship list <world> <entity_id>

# Event log
python -m src.cli.commands events <world> --entity <id> --type <type> --limit 50
```

---

## Module System

Modules extend Arcane Arsenal with game-specific features:

```python
class MyGameModule(Module):
    @property
    def name(self):
        return "my_game"

    @property
    def version(self):
        return "1.0.0"

    def register_component_types(self):
        return [HealthComponent, MagickaComponent]

    def register_relationship_types(self):
        return [OwnsRelationship]
```

**See [MODULE_GUIDE.md](MODULE_GUIDE.md) for details.**

---

## Design Principles

1. **Composition over Inheritance**: Build entities from components
2. **Explicit over Implicit**: All types registered, no magic strings
3. **Event-Driven**: Every state change emits an event
4. **Validation in Code**: Database stores data, Python enforces rules
5. **AI-Friendly**: Structured, typed data prevents hallucination

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific suites
pytest tests/unit/ -v
pytest tests/integration/ -v
```

---

## Development Status

**Phase 1**: Core Foundation ✅ Complete
- ECS architecture
- StateEngine API
- Web interface (Player & DM)
- Real-time multiplayer
- Module system
- Comprehensive test suite

**Phase 2**: Expanding game systems
- Additional modules (D&D 5e, Pathfinder, etc.)
- Enhanced UI features
- AI integration tools

---

## Project Structure

```
arcane-arsenal/
├── src/
│   ├── core/           # ECS engine, storage, events
│   ├── modules/        # Game system modules
│   ├── web/            # Flask app, templates, static
│   └── cli/            # Command-line tool
├── tests/              # Unit and integration tests
├── worlds/             # User world data (gitignored)
└── docs/               # Implementation guides
```

---

## Contributing

Personal project by Samuel. For questions or collaboration, please reach out through the repository.

---

**Status**: Phase 1 Complete ✅ | Multiplayer Ready 🎲 | Extensible 🔧
