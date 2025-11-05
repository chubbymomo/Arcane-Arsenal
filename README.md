# Arcane Arsenal

A roleplaying state manager built on Entity Component System (ECS) architecture. Designed to maintain RPG worlds in a way that prevents AI hallucination and enables versatile usage patterns.

## Overview

Arcane Arsenal provides:
- **Flexible Entity Composition**: Build any game object from reusable components
- **AI-Friendly State**: Explicit, structured data prevents LLM hallucination
- **Modular Architecture**: Add new game systems without touching core
- **Event-Driven**: Complete audit trail and network-ready from day one

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize a new world
python -m src.cli.commands init my_world

# Start web viewer
python -m src.web.server my_world
```

Visit http://localhost:5000 to view your world state.

## Architecture

```
Entity (ID + Name)
  └─> Components (typed data containers)
  └─> Relationships (explicit connections to other entities)
```

All state changes emit Events for complete traceability.

## Development Status

**Phase 1: Core Foundation** (In Progress)
- [x] Project structure
- [x] Database schema
- [ ] Storage layer
- [ ] State engine
- [ ] Core components module
- [ ] CLI tool
- [ ] Web viewer
- [ ] Tests

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for detailed implementation plan.

## Project Structure

```
arcane-arsenal/
├── src/
│   ├── core/          # State engine and storage
│   ├── modules/       # Component and game system modules
│   ├── web/           # Web viewer
│   └── cli/           # Command-line interface
├── tests/             # Unit and integration tests
├── worlds/            # User world data
├── schema.sql         # Database schema
└── PROJECT_PLAN.md    # Detailed architecture and plan
```

## Design Principles

1. **Composition over Inheritance**: ECS pattern for maximum flexibility
2. **Explicit over Implicit**: All relationships and types are registered
3. **Validation in Code**: Database stores data, Python handles business logic
4. **Event-Driven**: All state changes are trackable and syncable

## License

Personal project by Samuel. Contact for collaboration.

## Next Steps

After Phase 1 is complete:
- Character Manager module (HP, stats, inventory)
- AI DM integration
- Multiplayer networking
- Additional game system modules
