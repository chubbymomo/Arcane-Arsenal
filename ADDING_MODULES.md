# Adding Modules to Your World

Arcane Arsenal supports a modular system for game-specific components. This guide shows how to add modules like Elder Scrolls, D&D 5e, or your own custom modules.

## Quick Start: Adding a Module to Your World

Every world has a `config.json` file that controls which modules are loaded:

```bash
worlds/my_world/config.json
```

### Default Configuration (Core Only)

When you create a new world, it starts with only core components:

```json
{
  "world_name": "My World",
  "modules": [
    "core_components"
  ]
}
```

### Adding the Elder Scrolls Module

To add Elder Scrolls components (Magicka, Race, Shouts):

1. **Edit your world's config.json:**

```json
{
  "world_name": "Skyrim Campaign",
  "modules": [
    "core_components",
    "elder_scrolls"
  ]
}
```

2. **Restart the server:**

```bash
python -m src.cli.commands serve worlds/my_world
```

The Elder Scrolls module will automatically load and register its component types!

### Adding Multiple Modules

You can mix and match modules. For example, use Elder Scrolls races with D&D mechanics:

```json
{
  "world_name": "Hybrid Campaign",
  "modules": [
    "core_components",
    "elder_scrolls",
    "dnd_5e"
  ]
}
```

## Available Modules

### core_components (Always Loaded)

Core components work with any game system:
- `Identity` - Entity description
- `Position` - Spatial location (x, y, z, region)
- `Container` - Can hold other entities
- `PlayerCharacter` - Marks player-controlled characters

### elder_scrolls (Example Third-Party Module)

See `EXAMPLE_ELDER_SCROLLS_MODULE.md` for the complete implementation.

Components:
- `Magicka` - Magic resource pool
- `Race` - Elder Scrolls racial bonuses (Nord, Khajiit, etc.)
- `Shout` - Thu'um dragon shout abilities

### dnd_5e (Future Module)

*Not yet implemented - example for Phase 2*

Components:
- `Class` - D&D class and level
- `Abilities` - STR, DEX, CON, INT, WIS, CHA
- `Skills` - Proficiencies and bonuses
- `SpellSlots` - Spell slot tracking

## Creating Characters with Modules

Once a module is loaded, its components work seamlessly:

### Pure Elder Scrolls Character

```python
# Create entity
result = engine.create_entity("Lyris Titanborn")
entity_id = result.data['id']

# Core components (always available)
engine.add_component(entity_id, 'Identity', {
    'description': 'A Nord warrior of immense strength'
})
engine.add_component(entity_id, 'PlayerCharacter', {})

# Elder Scrolls components (from elder_scrolls module)
engine.add_component(entity_id, 'Race', {
    'race_name': 'Nord',
    'racial_ability': 'Battle Cry',
    'height_modifier': 1.05
})
engine.add_component(entity_id, 'Magicka', {
    'current': 120,
    'maximum': 120,
    'regen_rate': 3.0
})
```

### Hybrid Character (Elder Scrolls + D&D)

```python
# Entity with BOTH Elder Scrolls and D&D components!
result = engine.create_entity("Bjorn the Barbarian Dragonborn")
entity_id = result.data['id']

# Core
engine.add_component(entity_id, 'PlayerCharacter', {})

# Elder Scrolls module
engine.add_component(entity_id, 'Race', {
    'race_name': 'Nord',
    'racial_ability': 'Battle Cry'
})
engine.add_component(entity_id, 'Shout', {
    'known_shouts': [
        {'name': 'Fus Ro Dah', 'words_unlocked': 3, 'cooldown_seconds': 90}
    ]
})

# D&D 5e module
engine.add_component(entity_id, 'Class', {
    'class_name': 'Barbarian',
    'level': 5
})
engine.add_component(entity_id, 'Abilities', {
    'str': 18, 'dex': 14, 'con': 16,
    'int': 10, 'wis': 12, 'cha': 8
})
```

## Creating Your Own Module

See `EXAMPLE_ELDER_SCROLLS_MODULE.md` for a complete guide on creating a module.

Basic steps:

1. Create directory: `src/modules/my_module/`
2. Create `__init__.py` with Module subclass
3. Define component types (subclass ComponentTypeDefinition)
4. Add to your world's config.json
5. Restart server

### Import Standards

When creating modules, follow these import conventions for consistency:

**Use relative imports for intra-package imports** (within `src.modules`):
```python
# In src/modules/my_module/__init__.py
from ..base import Module, ComponentTypeDefinition  # ✅ Correct
from src.modules.base import Module                 # ❌ Avoid
```

**Use absolute imports for cross-package imports** (from `src.core`):
```python
# In src/modules/my_module/__init__.py
from src.core.state_engine import StateEngine      # ✅ Correct
from src.core.event_bus import Event              # ✅ Correct
```

**Use relative imports for intra-module imports** (within your module):
```python
# In src/modules/my_module/__init__.py
from .components import MyComponent                # ✅ Correct
from .events import my_event                      # ✅ Correct
```

**Why this matters:**
- Consistent imports make modules easier to maintain
- Relative imports for same-package code are more resilient to refactoring
- Absolute imports for cross-package code make dependencies explicit
- Follows Python best practices for package structure

## Module Safety

- **Core modules are safe** - They only register types, no code execution
- **Third-party modules should be reviewed** - The `initialize()` hook can run arbitrary code
- **Start with core only** - New worlds default to `["core_components"]` for safety

## Troubleshooting

### Module Not Loading

Check that:
1. Module directory exists in `src/modules/`
2. Module name in config.json matches directory name
3. Module has `__init__.py` with a Module subclass
4. Check server logs for import errors

### Component Type Not Found

Make sure:
1. Module is listed in config.json
2. Server was restarted after editing config.json
3. Component type name matches exactly (case-sensitive)

### Existing Worlds

Good news! With the auto-registration system (added in commit 8cf13da), **new component types automatically register to existing worlds**. Just add the module to config.json and restart!

## Benefits of the Module System

✅ **Mix and Match** - Use Elder Scrolls races with D&D classes
✅ **Pure ECS** - Entity type determined by component composition
✅ **No Core Changes** - Add game systems without modifying engine
✅ **Version Isolation** - Each module has independent versioning
✅ **Backward Compatible** - Worlds work with old or new modules

## Example Workflows

### Converting a World from D&D to Elder Scrolls

1. Edit config.json:
```json
{
  "modules": [
    "core_components",
    "elder_scrolls"  // removed dnd_5e
  ]
}
```

2. Restart server
3. Old D&D components remain in database but are no longer validated
4. New characters use Elder Scrolls components
5. You can even keep both modules and migrate characters gradually!

### Testing a New Module

1. Create a test world:
```bash
python -m src.cli.commands init worlds/test_es "ES Test"
```

2. Add module to config:
```json
{
  "modules": ["core_components", "elder_scrolls"]
}
```

3. Test the components
4. Once satisfied, add to your main world

## Advanced: Module Discovery

Currently, modules must be in `src/modules/` directory. Future enhancements may support:
- External module packages (via pip install)
- Module dependencies
- Module compatibility checking
- Hot-reloading modules
