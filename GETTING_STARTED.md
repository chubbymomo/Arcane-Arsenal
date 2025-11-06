# Getting Started with Arcane Arsenal

Arcane Arsenal is a TTRPG game engine using Entity Component System (ECS) architecture. Phase 1 is complete with full web interface, CLI tools, and module system.

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/arcane-arsenal.git
cd arcane-arsenal
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### 3. Run Tests (Verify Setup)

```bash
pytest tests/
# All 99 tests should pass ✅
```

### 4. Start the Web Interface

```bash
python src/web/server.py
```

Then visit **http://localhost:5000**

You'll see the **Realm Portal** (world selector) where you can:
- Create new realms (worlds) with different module combinations
- Select existing realms to edit
- Switch between realms

## Creating Your First Realm

### Via Web Interface (Recommended)

1. Visit http://localhost:5000
2. Click **"Forge New Realm"**
3. Enter realm details:
   - **Folder Name**: `my_first_world` (filesystem directory name)
   - **Realm Name**: `My First Campaign` (display name)
4. Select modules to include:
   - ✅ **core_components** (required - always included)
   - ✅ **rng** (dice rolling - recommended)
   - ☐ **fantasy_combat** (health, armor, weapons - optional)
5. Click **"Create Realm"**

Your realm is now active! You'll be redirected to the client interface where you can:
- Create entities (characters, locations, items)
- Add components to entities
- Create relationships between entities
- View event history

### Via CLI

```bash
# Initialize a new world
python -m src.cli.commands init worlds/my_world --name "My Campaign"

# Create entities
python -m src.cli.commands create --world worlds/my_world --entity "Theron the Brave"

# List entities
python -m src.cli.commands list --world worlds/my_world

# Add a component
python -m src.cli.commands add-component \
  --world worlds/my_world \
  --entity entity_abc123 \
  --type Identity \
  --data '{"description": "A brave adventurer"}'
```

## Web Interface Overview

Arcane Arsenal has two web interfaces:

### 1. Client Interface (Player View)
**URL**: http://localhost:5000/client

Features:
- Create and manage player characters
- View character sheets
- See world state from player perspective

### 2. Host Interface (GM/DM View)
**URL**: http://localhost:5000/host

Features:
- Full CRUD operations on entities, components, relationships
- Event history viewing
- Complete world management
- JSON editing with validation

## Understanding the Module System

Arcane Arsenal uses a **modular architecture**. Each realm can use different module combinations:

### Core Modules (Always Available)

- **core_components**: Identity, Position, Container, PlayerCharacter
- **rng**: Random number generation, dice rolling, Luck, RollModifier

### Optional Modules

- **fantasy_combat**: Health, Armor, Weapon components for combat

### Module Configuration

Each realm has a `config.json` file specifying which modules to load:

```json
{
  "world_name": "My Campaign",
  "modules": [
    "core_components",
    "rng",
    "fantasy_combat"
  ]
}
```

Modules are automatically:
- ✅ Loaded in dependency order
- ✅ Validated for dependencies
- ✅ Registered with the engine

See [ADDING_MODULES.md](ADDING_MODULES.md) for creating custom modules.

## Project Structure

```
arcane-arsenal/
├── src/
│   ├── core/                   # Core engine
│   │   ├── models.py          # Entity, Component, Relationship, Event
│   │   ├── storage.py         # SQLite persistence
│   │   ├── state_engine.py    # Main API
│   │   ├── event_bus.py       # Pub/sub events
│   │   └── module_loader.py   # Module system
│   │
│   ├── modules/               # Extensible modules
│   │   ├── base.py           # Module interfaces
│   │   ├── core_components/  # Core module
│   │   ├── rng/             # Dice rolling
│   │   └── fantasy_combat/  # Combat system
│   │
│   ├── cli/                  # Command-line interface
│   ├── web/                  # Web interface
│   │   ├── server.py        # Flask app
│   │   ├── blueprints/      # Client/Host routes
│   │   ├── templates/       # HTML templates
│   │   └── static/          # CSS/JS
│   │
├── tests/                    # 99 passing tests
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── test_*.py           # Module tests
│
├── worlds/                  # World data directories
│   └── my_world/
│       ├── world.db        # SQLite database
│       └── config.json     # Module configuration
│
├── schema.sql              # Database schema
├── requirements.txt        # Python dependencies
└── setup.py               # Package setup
```

## Key Documentation

| Document | Purpose |
|----------|---------|
| **README.md** | Project overview and features |
| **PROJECT_PLAN.md** | Complete architecture specification |
| **IMPLEMENTATION_SUMMARY.md** | Phase 1 completion status |
| **ADDING_MODULES.md** | Guide for creating custom modules |
| **WEB_EDITING_GUIDE.md** | Web interface tutorial |
| **THEMING_GUIDE.md** | CSS theming guidelines |
| **docs/ECS_ARCHITECTURE.md** | ECS pattern explanation |
| **CODEBASE_REVIEW.md** | Code quality review |

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_rng_module.py

# Run tests with coverage
pytest tests/ --cov=src
```

## Development Workflow

### Adding a New Component Type

1. Create component class in appropriate module
2. Inherit from `ComponentTypeDefinition`
3. Implement `get_schema()` method
4. Optional: Implement `validate_with_engine()` for advanced validation
5. Register in module's `register_component_types()` method

See [docs/ECS_ARCHITECTURE.md](docs/ECS_ARCHITECTURE.md) for details.

### Creating a Custom Module

1. Create directory in `src/modules/your_module/`
2. Create `__init__.py` with Module subclass
3. Define component types, events, relationships
4. Add to world's `config.json`

See [ADDING_MODULES.md](ADDING_MODULES.md) for detailed guide.

## Example: Creating a Character

### Via Python API

```python
from src.core.state_engine import StateEngine

# Load a world
engine = StateEngine('worlds/my_world')

# Create entity
result = engine.create_entity("Theron the Brave")
entity_id = result.data['id']

# Add components
engine.add_component(entity_id, 'Identity', {
    'description': 'A brave Nord warrior'
})

engine.add_component(entity_id, 'Position', {
    'x': 100, 'y': 200, 'z': 0, 'region': 'whiterun'
})

engine.add_component(entity_id, 'PlayerCharacter', {})

# Query for all player characters
players = engine.query_entities(['PlayerCharacter'])
```

### Via Web Interface

1. Go to http://localhost:5000/client
2. Click **"Create New Character"**
3. Fill in character details
4. Components are added automatically based on form

## Common Tasks

### Switch Between Realms

1. Click **"Realm Portal"** in top navigation
2. Select different realm from list
3. Or create new realm

### View All Entities

- **Client View**: http://localhost:5000/client/characters
- **Host View**: http://localhost:5000/host/entities

### Add Custom Components

```python
# Via API
engine.add_component(entity_id, 'health', {
    'current_hp': 100,
    'max_hp': 100,
    'temp_hp': 0
})

# Via Web (Host Interface)
1. Navigate to entity page
2. Click "Add Component"
3. Select component type
4. Fill JSON data
5. Submit
```

### View Event History

**Web Interface**:
- Go to http://localhost:5000/host/events
- Filter by entity or event type

**API**:
```python
events = engine.get_events(entity_id=entity_id, limit=50)
```

## Troubleshooting

### Module Not Loading

Check `worlds/my_world/config.json`:
```json
{
  "world_name": "My World",
  "modules": ["core_components", "rng"]
}
```

Ensure module names match directory names in `src/modules/`.

### Import Errors

```bash
# Reinstall in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Tests Failing

```bash
# Check Python version (requires 3.8+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Run single test for debugging
pytest tests/test_rng_module.py::TestDiceParser::test_simple_roll -v
```

## Next Steps

Now that you're set up:

1. **Explore the Web Interface**: Create entities, add components, experiment
2. **Read the Guides**:
   - [WEB_EDITING_GUIDE.md](WEB_EDITING_GUIDE.md) - Web interface tutorial
   - [ADDING_MODULES.md](ADDING_MODULES.md) - Create custom modules
   - [docs/ECS_ARCHITECTURE.md](docs/ECS_ARCHITECTURE.md) - Understand ECS pattern
3. **Build Custom Modules**: Add your own game-specific components
4. **Contribute**: Report issues, suggest features, submit PRs

## Phase 1 Complete ✅

Phase 1 is fully implemented with:
- ✅ Core ECS engine
- ✅ Module system with dependency resolution
- ✅ Web interface (client + host views)
- ✅ CLI tools
- ✅ RNG module with dice rolling
- ✅ 99 passing tests
- ✅ Comprehensive documentation

**Future Phases** (see PROJECT_PLAN.md):
- Phase 2: Character Manager
- Phase 3: AI Context Generation
- Phase 4: Networking

Happy world building! 🎲✨
