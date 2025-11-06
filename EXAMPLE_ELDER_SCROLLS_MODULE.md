# Example: Creating a Third-Party Module for Arcane Arsenal

This example shows how someone could create an "Elder Scrolls" module for Arcane Arsenal.

## Module Structure

```
src/modules/elder_scrolls/
├── __init__.py          # Main module class
├── magicka.py           # Magicka component
├── race.py              # Race component
└── shout.py             # Thu'um shout component
```

## Complete Implementation Example

### `elder_scrolls/__init__.py`

```python
"""
Elder Scrolls Module for Arcane Arsenal.

Adds Elder Scrolls-specific components and game mechanics.
"""

from typing import List
from ..base import Module, ComponentTypeDefinition, RelationshipTypeDefinition
from .magicka import MagickaComponent
from .race import RaceComponent
from .shout import ShoutComponent


class ElderScrollsModule(Module):
    """
    Elder Scrolls game system module.

    Provides TES-specific components like Magicka, Race, and Shouts.
    Compatible with core components for a complete VTT experience.
    """

    @property
    def name(self) -> str:
        return "elder_scrolls"

    @property
    def version(self) -> str:
        return "1.0.0"

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register Elder Scrolls components."""
        return [
            MagickaComponent(),
            RaceComponent(),
            ShoutComponent()
        ]

    def register_relationship_types(self) -> List[RelationshipTypeDefinition]:
        """Register Elder Scrolls relationships."""
        return []  # Could add guild_member, vampire_clan, etc.

    def initialize(self, engine):
        """Optional: Create default entities like holds, guilds."""
        # Example: Create the Companions guild
        result = engine.create_entity("The Companions")
        if result.success:
            guild_id = result.data['id']
            engine.add_component(guild_id, 'Identity', {
                'description': 'A guild of warriors in Whiterun'
            })


# Export
__all__ = ['ElderScrollsModule']
```

### `elder_scrolls/magicka.py`

```python
"""Magicka component for magic resource tracking."""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class MagickaComponent(ComponentTypeDefinition):
    """
    Magicka resource component.

    Tracks current and maximum magicka for spellcasting.
    Compatible with core PlayerCharacter component.
    """

    type = 'Magicka'
    description = 'Magic resource for spellcasting'
    schema_version = '1.0.0'
    module = 'elder_scrolls'

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Current magicka"
                },
                "maximum": {
                    "type": "number",
                    "minimum": 1,
                    "description": "Maximum magicka"
                },
                "regen_rate": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Magicka regeneration per second"
                }
            },
            "required": ["current", "maximum", "regen_rate"],
            "additionalProperties": False
        }

    @staticmethod
    def validate(data: Dict[str, Any]) -> None:
        import jsonschema
        schema = MagickaComponent.get_schema()
        jsonschema.validate(data, schema)

        # Custom validation: current can't exceed maximum
        if data['current'] > data['maximum']:
            raise jsonschema.ValidationError(
                "Current magicka cannot exceed maximum"
            )
```

### `elder_scrolls/race.py`

```python
"""Race component for Elder Scrolls racial bonuses."""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class RaceComponent(ComponentTypeDefinition):
    """
    Character race component.

    Defines racial identity and bonuses for Elder Scrolls characters.
    """

    type = 'Race'
    description = 'Character race with bonuses and abilities'
    schema_version = '1.0.0'
    module = 'elder_scrolls'

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "race_name": {
                    "type": "string",
                    "enum": [
                        "Nord", "Imperial", "Breton", "Redguard",
                        "High Elf", "Wood Elf", "Dark Elf", "Orc",
                        "Khajiit", "Argonian"
                    ]
                },
                "racial_ability": {
                    "type": "string",
                    "description": "Name of racial power"
                },
                "height_modifier": {
                    "type": "number",
                    "description": "Height multiplier"
                }
            },
            "required": ["race_name", "racial_ability"],
            "additionalProperties": False
        }
```

### `elder_scrolls/shout.py`

```python
"""Thu'um shout abilities component."""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class ShoutComponent(ComponentTypeDefinition):
    """
    Thu'um shout component.

    Tracks known dragon shouts and their cooldowns.
    """

    type = 'Shout'
    description = 'Dragon shout abilities'
    schema_version = '1.0.0'
    module = 'elder_scrolls'

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "known_shouts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "words_unlocked": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 3
                            },
                            "cooldown_seconds": {"type": "number"}
                        },
                        "required": ["name", "words_unlocked", "cooldown_seconds"]
                    }
                }
            },
            "required": ["known_shouts"],
            "additionalProperties": False
        }
```

## How to Load the Module

Arcane Arsenal uses **configuration-based module loading**. Modules are specified in each world's `config.json` file, allowing different worlds to use different module combinations without modifying core code.

### Current Approach: Configuration-Based Loading

**Step 1:** Create your module in `src/modules/elder_scrolls/`

**Step 2:** Create or update `config.json` in your world directory:

```json
{
  "world_name": "Skyrim Campaign",
  "modules": [
    "core_components",
    "rng",
    "elder_scrolls"
  ]
}
```

**Step 3:** The module loads automatically when you open the world!

```python
# StateEngine automatically discovers and loads modules based on config.json
engine = StateEngine(world_path='worlds/skyrim')

# Modules are loaded in dependency order:
# 1. core_components (required by elder_scrolls)
# 2. rng (core module)
# 3. elder_scrolls (your custom module)
```

### Module Auto-Registration

The module system automatically:
- ✅ Resolves dependencies (elder_scrolls requires core_components)
- ✅ Validates all dependencies are available
- ✅ Loads modules in correct order (topological sort)
- ✅ Registers all component types, relationship types, and event types
- ✅ Initializes module-specific systems

### Adding Your Module

Place your `ElderScrollsModule` class in `src/modules/elder_scrolls/__init__.py` and it will be auto-discovered. No core code modification needed!

See [ADDING_MODULES.md](ADDING_MODULES.md) for detailed instructions on module development and configuration.

## Creating a Character with Elder Scrolls Components

Once loaded, the module components work seamlessly:

```python
# Create a Nord Dragonborn character
result = engine.create_entity("Bjorn the Dragonborn")
entity_id = result.data['id']

# Add core components (work with ANY module)
engine.add_component(entity_id, 'Identity', {
    'description': 'A Nord warrior and Dragonborn'
})
engine.add_component(entity_id, 'Position', {
    'x': 100, 'y': 200, 'z': 0, 'region': 'whiterun'
})
engine.add_component(entity_id, 'PlayerCharacter', {})

# Add Elder Scrolls-specific components
engine.add_component(entity_id, 'Race', {
    'race_name': 'Nord',
    'racial_ability': 'Battle Cry',
    'height_modifier': 1.03
})
engine.add_component(entity_id, 'Magicka', {
    'current': 100,
    'maximum': 100,
    'regen_rate': 3.0
})
engine.add_component(entity_id, 'Shout', {
    'known_shouts': [
        {
            'name': 'Fus Ro Dah',
            'words_unlocked': 3,
            'cooldown_seconds': 90
        },
        {
            'name': 'Wuld Nah Kest',
            'words_unlocked': 2,
            'cooldown_seconds': 30
        }
    ]
})
```

## Benefits of This Architecture

1. **Independent Development** - Third parties can create modules without modifying core
2. **Mix and Match** - Use Elder Scrolls race with D&D classes
3. **Version Isolation** - Each module has its own version
4. **Clean Separation** - Core engine knows nothing about Elder Scrolls
5. **Full ECS** - Entity type is determined by component composition

## Publishing a Module

A third-party developer could:

1. Create the module in their own repo
2. Publish to PyPI as `arcane-arsenal-elder-scrolls`
3. Users install: `pip install arcane-arsenal-elder-scrolls`
4. Place in `src/modules/elder_scrolls/`
5. Module auto-loads (with discovery system)

## Example: Mixed Character

You can even mix D&D and Elder Scrolls:

```python
# A character with BOTH D&D and Elder Scrolls components!
entity_id = create_character("Weird Hybrid")

# Core (works everywhere)
add_component('PlayerCharacter', {})
add_component('Position', {'x': 0, 'y': 0, 'z': 0, 'region': 'tavern'})

# Elder Scrolls
add_component('Race', {'race_name': 'Nord', ...})
add_component('Magicka', {'current': 150, 'maximum': 150, ...})

# D&D (from future dnd_5e module)
add_component('Class', {'class_name': 'Barbarian', 'level': 5})
add_component('Abilities', {'str': 18, 'dex': 14, ...})

# This entity is BOTH a Nord and a Barbarian!
```
