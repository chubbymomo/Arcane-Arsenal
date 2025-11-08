# Getting Started with Arcane Arsenal

Quick guide to setting up and using Arcane Arsenal.

---

## Installation

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/arcane-arsenal.git
cd arcane-arsenal

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
# Run tests
pytest tests/ -v

# All tests should pass ✅
```

---

## Create Your First World

### Option 1: Web Interface (Recommended)

```bash
# Start server
python src/web/server.py
```

Visit **http://localhost:5000**:

1. Click **"Forge New Realm"**
2. Configure your world:
   - **Folder Name**: `my_campaign` (filesystem name)
   - **Realm Name**: `My First Campaign` (display name)
3. Select modules:
   - ✅ `core_components` (required - Identity, Position)
   - ✅ `rng` (recommended - dice rolling)
   - ☐ `fantasy_combat` (optional - Health, Armor, Weapons)
4. Click **"Create Realm"**

You're now in the world! Navigate to:
- `/client` - Player interface
- `/host` - DM interface

### Option 2: CLI

```bash
# Initialize world
python -m src.cli.commands init worlds/my_campaign --name "My Campaign"

# Start web server for that world
python src/web/server.py worlds/my_campaign
```

---

## Understanding the Interface

### Player Interface (`/client`)

**For Players:**
- Create and select characters
- View character sheets
- Roll dice (if RNG module enabled)
- See inventory and equipment

**URL**: http://localhost:5000/client

### DM Interface (`/host`)

**For Game Masters:**
- Create/edit/delete entities
- Add/remove components
- Create relationships
- View event history
- Manage world state

**URL**: http://localhost:5000/host

---

## Your First Entity

### Via Web (DM Interface)

1. Go to http://localhost:5000/host
2. Click **"Create New Entity"**
3. Enter name: `Theron the Brave`
4. Click **"Create Entity"**
5. Click the entity name to view details
6. Click **"Add Component"**
7. Select `Identity` component
8. Enter JSON: `{"description": "A brave warrior"}`
9. Click **"Add Component"**

### Via CLI

```bash
# Set world path for convenience
WORLD=worlds/my_campaign

# Create entity
python -m src.cli.commands entity create $WORLD "Theron the Brave"
# Output: entity_abc123 (copy this ID)

# Add Identity component
python -m src.cli.commands component add $WORLD entity_abc123 Identity \
  '{"description": "A brave warrior"}'

# Add Position component
python -m src.cli.commands component add $WORLD entity_abc123 Position \
  '{"x": 100, "y": 200, "region": "tavern"}'

# List entity components
python -m src.cli.commands component list $WORLD entity_abc123
```

---

## Creating a Scene

Let's create a tavern with characters and items:

```bash
WORLD=worlds/my_campaign

# Create tavern location
python -m src.cli.commands entity create $WORLD "The Golden Tankard"
# TAVERN=<entity_id from output>

# Add location components
python -m src.cli.commands component add $WORLD $TAVERN Identity \
  '{"description": "A cozy tavern filled with adventurers"}'

python -m src.cli.commands component add $WORLD $TAVERN Position \
  '{"x": 100, "y": 100, "region": "town_center"}'

# Create character
python -m src.cli.commands entity create $WORLD "Theron"
# HERO=<entity_id from output>

python -m src.cli.commands component add $WORLD $HERO Identity \
  '{"description": "A brave warrior"}'

python -m src.cli.commands component add $WORLD $HERO PlayerCharacter '{}'

# Place hero at tavern
python -m src.cli.commands relationship create $WORLD $HERO $TAVERN located_at

# Create an item
python -m src.cli.commands entity create $WORLD "Rusty Sword"
# SWORD=<entity_id from output>

python -m src.cli.commands component add $WORLD $SWORD Identity \
  '{"description": "An old but serviceable weapon"}'

# Place sword in tavern
python -m src.cli.commands relationship create $WORLD $TAVERN $SWORD contains
```

Now view in browser at http://localhost:5000/host to see your tavern scene!

---

## Working with Modules

### Enable Modules for a World

Edit `worlds/my_campaign/config.json`:

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

Restart the web server to load the new modules.

### Available Built-in Modules

**core_components** (required)
- `Identity`: Description, tags
- `Position`: Spatial positioning

**rng** (recommended)
- Real-time dice rolling
- Roll history tracking
- WebSocket-synced results

**fantasy_combat**
- `Health`: HP tracking
- `Armor`: AC/defense values
- `Weapon`: Attack stats

---

## Using the CLI

### Common Commands

```bash
# World management
python -m src.cli.commands init <world_path> --name "Name"

# Entity operations
python -m src.cli.commands entity create <world> "Name"
python -m src.cli.commands entity list <world>
python -m src.cli.commands entity get <world> <entity_id>
python -m src.cli.commands entity delete <world> <entity_id>

# Component operations
python -m src.cli.commands component add <world> <entity_id> <type> '<json>'
python -m src.cli.commands component list <world> <entity_id>
python -m src.cli.commands component get <world> <entity_id> <type>
python -m src.cli.commands component remove <world> <entity_id> <type>

# Relationship operations
python -m src.cli.commands relationship create <world> <from> <to> <type>
python -m src.cli.commands relationship list <world> <entity_id>

# Event log
python -m src.cli.commands events <world> --limit 50
python -m src.cli.commands events <world> --entity <id>
python -m src.cli.commands events <world> --type entity_created

# Type registry
python -m src.cli.commands types components <world>
python -m src.cli.commands types relationships <world>
```

---

## Next Steps

### Learn the Architecture

Read the implementation guides to understand how to extend Arcane Arsenal:
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Backend principles
- **[FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md)** - Frontend principles
- **[MODULE_GUIDE.md](MODULE_GUIDE.md)** - Creating modules

### Technical References

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Complete schemas and APIs
- **[FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)** - Frontend tutorials

### Create Your Own Module

See **[MODULE_GUIDE.md](MODULE_GUIDE.md)** for:
- Module structure
- Component type definitions
- Relationship types
- Event handling
- UI integration

---

## Troubleshooting

### "Module not found" error

```bash
# Install in development mode
pip install -e .
```

### "No such file or directory: worlds/..."

```bash
# Initialize the world first
python -m src.cli.commands init worlds/my_world --name "My World"
```

### Tests failing

```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Run tests with verbose output
pytest tests/ -v
```

### Web interface not loading

```bash
# Check if port 5000 is in use
# Try a different port
python src/web/server.py worlds/my_world --port 8080
```

---

## Quick Reference

### Essential JSON Schemas

**Identity Component**
```json
{
  "description": "Text description",
  "tags": ["optional", "list"]
}
```

**Position Component**
```json
{
  "x": 100,
  "y": 200,
  "z": 0,
  "region": "region_name_or_entity_id"
}
```

**Health Component** (fantasy_combat module)
```json
{
  "current_hp": 50,
  "max_hp": 100,
  "temp_hp": 0
}
```

**PlayerCharacter Component**
```json
{}
```

### Common Relationship Types

- `located_at`: Entity is at a location
- `contains`: Container holds another entity
- `owns`: Entity owns another entity
- `equipped_in`: Item equipped in slot

---

## Getting Help

1. Check documentation:
   - Implementation guides for architecture
   - PROJECT_PLAN.md for technical details
   - This guide for practical usage

2. Run tests to verify setup:
   ```bash
   pytest tests/ -v
   ```

3. Check the event log for errors:
   ```bash
   python -m src.cli.commands events <world> --limit 50
   ```

---

**Happy worldbuilding! 🎲**
