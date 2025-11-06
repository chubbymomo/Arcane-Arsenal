# RNG Module

**Random Number Generation for TTRPG Dice Rolls**

The RNG module provides a complete dice rolling system with support for standard TTRPG mechanics like advantage/disadvantage, critical hits, and entity-specific modifiers.

## Features

- ✅ **Dice Notation Parsing** - Supports standard notation: `1d20`, `3d6+5`, `2d8+1d6+3`
- ✅ **Advantage/Disadvantage** - D&D 5e style mechanics (roll twice, keep higher/lower)
- ✅ **Critical Detection** - Automatic detection of natural 20s and 1s
- ✅ **Entity Modifiers** - Luck bonuses, advantage grants, roll-specific modifiers
- ✅ **Event-Driven** - All rolls emit events for audit trail and reaction systems
- ✅ **Seeded Random** - Deterministic rolls for testing and combat replay
- ✅ **Comprehensive Tests** - 24 passing tests covering all functionality

## Roll Type Registry

**Important for AI Agents:** Roll types are NOT free-form strings. They must be registered by modules.

### Core Roll Types

The RNG module registers these core roll types:
- `attack` - Attack roll to hit a target (combat)
- `damage` - Damage roll after successful hit (combat)
- `saving_throw` - Save against effects (saving_throw)
- `skill_check` - Skill-based check (skill)
- `ability_check` - Raw ability check (ability)
- `initiative` - Turn order determination (combat)

### Querying Valid Roll Types

```python
# Get all registered roll types
roll_types = engine.storage.get_roll_types()

# Via API (for AI agents)
GET /api/roll_types
# Returns: {"roll_types": [{"type": "attack", "description": "...", "category": "combat", ...}, ...]}
```

### Registering Custom Roll Types

Modules can register additional roll types:

```python
from src.modules.base import Module, RollTypeDefinition

class SkillsModule(Module):
    def register_roll_types(self):
        return [
            RollTypeDefinition(
                type='stealth_check',
                description='Stealth skill check',
                module='skills',
                category='skill'
            ),
            RollTypeDefinition(
                type='perception_check',
                description='Perception skill check',
                module='skills',
                category='skill'
            )
        ]
```

### Validation

Invalid roll types are **rejected**:

```python
# This will be rejected - no event emitted
engine.event_bus.publish(Event.create(
    event_type='roll.requested',
    data={
        'roll_type': 'made_up_type',  # ❌ Not registered!
        ...
    }
))
```

## Components

### Luck Component

Affects all rolls made by an entity. Represents character traits, buffs, or curses.

```python
engine.add_component(entity_id, "Luck", {
    "global_bonus": 2,            # +2 to all rolls
    "advantage_on": ["attack"],   # Advantage on attack rolls
    "disadvantage_on": [],        # No disadvantage
    "reroll_ones": False,         # Halfling Luck (future)
    "critical_range": 20          # Crit on 20 (19 for improved crit)
})
```

### RollModifier Component

Affects specific types of rolls. Represents equipment bonuses, spell effects, or situational modifiers.

```python
engine.add_component(entity_id, "RollModifier", {
    "modifier_type": "attack",    # What this affects
    "bonus": 3,                   # +3 to attack rolls
    "source": "Sword of Smiting", # Source of bonus
    "conditions": {}              # Optional conditions (future)
})
```

## Events

### roll.requested

Published when an entity wants to make a roll. The RNG module listens for this event and processes the roll.

```python
engine.event_bus.publish(Event.create(
    event_type='roll.requested',
    entity_id=player_id,
    actor_id=player_id,
    data={
        'entity_id': player_id,
        'notation': '1d20+5',
        'roll_type': 'attack',
        'purpose': 'Attack goblin with sword',
        'target_id': goblin_id,  # Optional
        'force_advantage': False,  # Optional
        'force_disadvantage': False  # Optional
    }
))
```

### roll.completed

Published when a roll finishes. Contains full breakdown for display and audit trail.

```python
def on_roll_completed(event):
    print(f"Total: {event.data['total']}")
    print(f"Breakdown: {event.data['breakdown']}")
    # Example: "1d20 with advantage: [18, 7] → kept 18 | modifier: +5 | **Total: 23**"

    if event.data['natural_20']:
        print("CRITICAL HIT!")

engine.event_bus.subscribe('roll.completed', on_roll_completed)
```

## Usage Examples

### Basic Roll

```python
# Via events (recommended - applies entity modifiers)
engine.event_bus.publish(Event.create(
    event_type='roll.requested',
    entity_id=player_id,
    actor_id=player_id,
    data={
        'entity_id': player_id,
        'notation': '1d20+5',
        'roll_type': 'attack',
        'purpose': 'Basic attack'
    }
))

# Direct (testing only - no entity modifiers)
from src.modules.rng import RNGModule
rng = RNGModule()
result = rng.roll_direct('1d20+5')
print(result.total)  # 1-25
```

### Advantage/Disadvantage

```python
# Entity with Luck component grants advantage
engine.add_component(player_id, "Luck", {
    "global_bonus": 0,
    "advantage_on": ["attack", "saving_throw"],
    "disadvantage_on": [],
    "reroll_ones": False,
    "critical_range": 20
})

# Request attack roll (will automatically have advantage)
engine.event_bus.publish(Event.create(
    event_type='roll.requested',
    entity_id=player_id,
    actor_id=player_id,
    data={
        'entity_id': player_id,
        'notation': '1d20',
        'roll_type': 'attack',
        'purpose': 'Attack with advantage'
    }
))
# Result: Rolls [18, 7] → keeps 18
```

### Entity Modifiers

```python
# Add global luck bonus
engine.add_component(player_id, "Luck", {
    "global_bonus": 2,  # +2 to all rolls
    "advantage_on": [],
    "disadvantage_on": [],
    "reroll_ones": False,
    "critical_range": 20
})

# Add magic weapon bonus
engine.add_component(weapon_id, "RollModifier", {
    "modifier_type": "attack",
    "bonus": 3,
    "source": "Flametongue Sword",
    "conditions": {}
})

# Roll with notation "1d20"
# Actual roll: "1d20+5" (2 from luck + 3 from weapon)
```

### Critical Hits

```python
def handle_attack(event):
    if event.data['natural_20']:
        # Double damage dice on crit
        damage_notation = "4d6"  # Normally 2d6
        engine.event_bus.publish(Event.create(
            event_type='roll.requested',
            entity_id=event.data['entity_id'],
            actor_id=event.data['entity_id'],
            data={
                'entity_id': event.data['entity_id'],
                'notation': damage_notation,
                'roll_type': 'damage',
                'purpose': 'Critical hit damage'
            }
        ))

engine.event_bus.subscribe('roll.completed', handle_attack)
```

## Dice Notation Reference

| Notation | Meaning | Example Result |
|----------|---------|----------------|
| `1d20` | Single d20 | 13 |
| `3d6` | Three d6 | 11 (3+4+4) |
| `1d20+5` | d20 plus modifier | 18 (13+5) |
| `2d8+1d6+3` | Multiple dice groups | 16 (5+7+2+3) |
| `1d20-2` | d20 with penalty | 11 (13-2) |

**Supported:**
- Standard dice notation (XdY)
- Positive and negative modifiers
- Multiple dice groups in one roll
- Complex expressions (2d8+1d6+3)

**Future Support:**
- Keep highest: `4d6k3` (roll 4d6, keep highest 3)
- Exploding dice: `1d6!` (reroll on max)
- Reroll mechanics: `1d20r1` (reroll 1s)

## Integration with Other Systems

### Combat System

```python
class CombatModule(Module):
    def on_attack_action(self, event):
        attacker_id = event.data['attacker_id']
        target_id = event.data['target_id']

        # Request attack roll
        engine.event_bus.publish(Event.create(
            event_type='roll.requested',
            entity_id=attacker_id,
            actor_id=attacker_id,
            data={
                'entity_id': attacker_id,
                'notation': '1d20',
                'roll_type': 'attack',
                'purpose': f'Attack {target_id}',
                'target_id': target_id
            }
        ))

    def on_roll_completed(self, event):
        if event.data['roll_type'] == 'attack':
            total = event.data['total']
            # Compare to target AC, roll damage if hit
```

### Skill Check System

```python
def make_skill_check(entity_id, skill, dc):
    """Request a skill check roll."""
    # Get skill modifier from entity
    skills = engine.get_component(entity_id, 'Skills')
    modifier = skills.data.get(skill, 0)

    # Request roll
    engine.event_bus.publish(Event.create(
        event_type='roll.requested',
        entity_id=entity_id,
        actor_id=entity_id,
        data={
            'entity_id': entity_id,
            'notation': f'1d20+{modifier}',
            'roll_type': 'skill_check',
            'purpose': f'{skill.title()} check (DC {dc})'
        }
    ))
```

## Testing

The RNG module includes comprehensive tests:

```bash
# Run all RNG tests
pytest tests/test_rng_module.py -v

# Run specific test category
pytest tests/test_rng_module.py::TestDiceParser -v
pytest tests/test_rng_module.py::TestDiceRoller -v
pytest tests/test_rng_module.py::TestRNGModule -v
```

**Test Coverage:**
- ✅ Dice notation parsing (8 tests)
- ✅ Dice rolling mechanics (11 tests)
- ✅ Module integration (5 tests)

## Architecture

```
src/modules/rng/
├── __init__.py           # RNGModule class (system logic)
├── dice_parser.py        # Dice notation parser
├── roller.py             # Core rolling logic
├── components.py         # Luck & RollModifier components
├── events.py            # Event definitions
└── README.md           # This file
```

**Key Classes:**
- `RNGModule` - Main system, subscribes to roll.requested events
- `DiceParser` - Parses notation like "1d20+5" into structured format
- `DiceRoller` - Performs actual rolls with advantage/disadvantage
- `RollResult` - Complete result with breakdown and metadata

## Configuration

### Load as Core Module

The RNG module is marked as `is_core = True`, meaning it's loaded automatically:

```python
# In config.json
{
    "modules": ["core_components", "rng", "fantasy_combat"]
}
```

### Seeded Random (Testing/Replay)

```python
# Create with seed for deterministic rolls
rng = RNGModule(seed=12345)

# All rolls will be deterministic
result1 = rng.roll_direct('3d6')
result2 = rng.roll_direct('3d6')  # Same result

# Change seed
rng.roller.set_seed(67890)
```

## Future Enhancements

- [ ] Exploding dice (`1d6!`)
- [ ] Keep highest (`4d6k3`)
- [ ] Reroll mechanics (`1d20r1`)
- [ ] Target numbers & success counting
- [ ] Dice pools (Shadowrun, World of Darkness)
- [ ] Reroll tokens (use Luck component data)
- [ ] Improved critical range (already supported via Luck.critical_range)

## See Also

- [ECS Architecture Guide](../../../docs/ECS_ARCHITECTURE.md) - Understanding systems and modules
- [Module System](../../modules/base.py) - How to create modules
- [Event Bus](../../core/event_bus.py) - Event-driven architecture
