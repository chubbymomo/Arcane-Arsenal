# ECS Architecture Guide

## Overview

Arcane Arsenal uses an **Entity-Component-System (ECS)** architecture with event-driven systems. This document explains how each piece works and how they fit together.

## Core Concepts

### Entity
**What:** A unique game object (character, item, location)
**Implementation:** Just an ID + minimal metadata (name, timestamps)
**File:** `src/core/models.py:40-96`

```python
entity = engine.create_entity("Theron the Brave")
# Returns: Entity(id="entity_abc123", name="Theron the Brave", ...)
```

### Component
**What:** Pure data attached to entities
**Implementation:** Typed data blobs validated with JSON schemas
**File:** `src/core/models.py:99-171`

```python
# Add Position component
engine.add_component(entity.id, "Position", {
    "x": 100,
    "y": 200,
    "z": 0,
    "region": "tavern"
})

# Add Health component
engine.add_component(entity.id, "Health", {
    "current_hp": 50,
    "max_hp": 50
})
```

**Key principle:** Components have NO behavior, only data

### System
**What:** Game logic that operates on entities with specific components
**Implementation:** Event-driven via modules (traditional game loop not used)
**File:** Implemented in module `initialize()` and `on_event()` methods

```python
class CombatModule(Module):
    def initialize(self, engine: StateEngine):
        # Subscribe to combat events
        engine.event_bus.subscribe('player.attack', self.process_attack)

    def process_attack(self, event: Event):
        # Query for entities with combat components
        attacker_id = event.data['attacker_id']
        target_id = event.data['target_id']

        # Get components
        weapon = engine.get_component(attacker_id, 'Weapon')
        health = engine.get_component(target_id, 'Health')

        # Apply game logic
        damage = weapon['damage']
        new_hp = max(0, health['current_hp'] - damage)

        # Update state
        engine.update_component(target_id, 'Health', {
            'current_hp': new_hp,
            'max_hp': health['max_hp']
        })
```

**Key principle:** Systems contain ALL game logic

### Engine (StateEngine)
**What:** Central coordinator for all ECS operations
**Implementation:** Single API for all entity/component operations
**File:** `src/core/state_engine.py`

```python
# Entity operations
entity = engine.create_entity("Player")
entities = engine.list_entities()

# Component operations
engine.add_component(entity_id, component_type, data)
engine.update_component(entity_id, component_type, data)
engine.remove_component(entity_id, component_type)

# Queries (the "Node" pattern)
players = engine.query_entities(['PlayerCharacter', 'Position'])
```

### Node (Query Pattern)
**What:** Selecting entities that match a component signature
**Implementation:** `query_entities()` method
**File:** `src/core/state_engine.py:785`

```python
# Find all entities with Position AND Health components
living_positioned = engine.query_entities(['Position', 'Health'])

# Find all player characters
players = engine.query_entities(['PlayerCharacter'])

# Find all containers in the world
containers = engine.query_entities(['Container', 'Position'])
```

**Key principle:** Queries use AND logic - entity must have ALL specified components

## Architecture Comparison

### Standard ECS (Game Engine Style)

```
┌─────────────────────────────────────┐
│ Game Loop                            │
│  ├─ MovementSystem.update()         │
│  ├─ CombatSystem.update()           │
│  ├─ AISystem.update()               │
│  └─ RenderSystem.update()           │
└─────────────────────────────────────┘
         ↓ 60 times per second
┌─────────────────────────────────────┐
│ Engine                               │
│  ├─ query_entities(['Pos', 'Vel'])  │
│  ├─ get_component()                  │
│  └─ update_component()               │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Storage                              │
│  ├─ Entities                         │
│  └─ Components                       │
└─────────────────────────────────────┘
```

**Used for:** Real-time games (FPS, platformers, etc.)

### Arcane Arsenal (Event-Driven Style)

```
┌─────────────────────────────────────┐
│ Web Request / User Action            │
│  └─ "Player attacks goblin"          │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Event Bus                            │
│  └─ publish('player.attack')         │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ CombatModule (System)                │
│  └─ handle_attack()                  │
│      ├─ query_entities()             │
│      ├─ get_component()              │
│      └─ update_component()           │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Engine                               │
│  └─ Component CRUD + Validation      │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Storage (SQLite)                     │
│  ├─ Entities                         │
│  ├─ Components                       │
│  └─ Event Log (audit trail)          │
└─────────────────────────────────────┘
```

**Used for:** Turn-based, web-based, or command-driven games

## Implementation Pattern for Systems

### Step 1: Define Components

```python
# src/modules/my_module/components.py
from src.modules.base import ComponentTypeDefinition

class StaminaComponent(ComponentTypeDefinition):
    def get_name(self) -> str:
        return "Stamina"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current": {"type": "number"},
                "max": {"type": "number"},
                "regen_rate": {"type": "number"}
            },
            "required": ["current", "max"]
        }
```

### Step 2: Define Events

```python
# src/modules/my_module/events.py
from src.modules.base import EventTypeDefinition

class ActionPerformedEvent(EventTypeDefinition):
    def get_name(self) -> str:
        return "action.performed"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string"},
                "action_type": {"type": "string"},
                "stamina_cost": {"type": "number"}
            },
            "required": ["entity_id", "action_type"]
        }
```

### Step 3: Implement System Logic in Module

```python
# src/modules/my_module/__init__.py
from src.modules.base import Module
from src.core.event_bus import Event

class StaminaModule(Module):
    @property
    def name(self) -> str:
        return "stamina_system"

    def register_component_types(self):
        return [StaminaComponent()]

    def register_event_types(self):
        return [ActionPerformedEvent()]

    def initialize(self, engine):
        """Called when module loads - set up event listeners"""
        self.engine = engine

        # Subscribe to action events
        engine.event_bus.subscribe('action.performed', self.on_action_performed)

        # Subscribe to time passing (if you have tick events)
        engine.event_bus.subscribe('time.tick', self.on_time_tick)

    def on_action_performed(self, event: Event):
        """System logic: Reduce stamina when actions are performed"""
        entity_id = event.data['entity_id']
        stamina_cost = event.data.get('stamina_cost', 10)

        # Get stamina component
        stamina = self.engine.get_component(entity_id, 'Stamina')
        if not stamina:
            return  # Entity doesn't have stamina

        # Reduce stamina
        new_stamina = max(0, stamina['current'] - stamina_cost)

        # Update component
        self.engine.update_component(entity_id, 'Stamina', {
            'current': new_stamina,
            'max': stamina['max'],
            'regen_rate': stamina['regen_rate']
        })

        # Publish exhaustion event if needed
        if new_stamina == 0:
            self.engine.event_bus.publish(Event(
                event_type='character.exhausted',
                entity_id=entity_id,
                data={}
            ))

    def on_time_tick(self, event: Event):
        """System logic: Regenerate stamina over time"""
        # Query all entities with Stamina
        entities = self.engine.query_entities(['Stamina'])

        for entity in entities:
            stamina = self.engine.get_component(entity.id, 'Stamina')

            # Regenerate if not at max
            if stamina['current'] < stamina['max']:
                new_stamina = min(
                    stamina['max'],
                    stamina['current'] + stamina['regen_rate']
                )

                self.engine.update_component(entity.id, 'Stamina', {
                    'current': new_stamina,
                    'max': stamina['max'],
                    'regen_rate': stamina['regen_rate']
                })
```

### Step 4: Trigger System from Web Routes

```python
# src/web/blueprints/client.py
@client_bp.route('/action/attack', methods=['POST'])
@require_world
def attack():
    engine = get_engine()

    attacker_id = session.get('character_id')
    target_id = request.form.get('target_id')

    # Publish event (system will handle it)
    engine.event_bus.publish(Event(
        event_type='action.performed',
        entity_id=attacker_id,
        actor_id=attacker_id,
        data={
            'entity_id': attacker_id,
            'action_type': 'attack',
            'target_id': target_id,
            'stamina_cost': 20
        }
    ))

    # The StaminaModule and CombatModule will react to this event

    flash("Attack executed!", "success")
    return redirect(url_for('client.index'))
```

## Best Practices

### 1. Components are ONLY Data
❌ **Wrong:**
```python
class HealthComponent:
    def take_damage(self, amount):
        self.current_hp -= amount
```

✅ **Correct:**
```python
class HealthComponent(ComponentTypeDefinition):
    def get_schema(self):
        return {
            "type": "object",
            "properties": {
                "current_hp": {"type": "number"},
                "max_hp": {"type": "number"}
            }
        }

# Damage logic goes in CombatSystem, not component
```

### 2. Systems Contain ALL Logic
❌ **Wrong:**
```python
# Logic scattered in routes
@client_bp.route('/attack')
def attack():
    weapon = engine.get_component(attacker_id, 'Weapon')
    health = engine.get_component(target_id, 'Health')
    new_hp = health['current_hp'] - weapon['damage']  # Combat logic in route!
    engine.update_component(target_id, 'Health', {'current_hp': new_hp})
```

✅ **Correct:**
```python
# Routes publish events
@client_bp.route('/attack')
def attack():
    engine.event_bus.publish(Event(
        event_type='combat.attack',
        data={'attacker_id': attacker_id, 'target_id': target_id}
    ))

# CombatSystem handles logic
class CombatModule(Module):
    def on_attack(self, event: Event):
        # All combat logic centralized here
        weapon = self.engine.get_component(event.data['attacker_id'], 'Weapon')
        armor = self.engine.get_component(event.data['target_id'], 'Armor')
        health = self.engine.get_component(event.data['target_id'], 'Health')

        # Calculate damage with armor, crits, resistances, etc.
        damage = self.calculate_damage(weapon, armor)
        new_hp = max(0, health['current_hp'] - damage)

        self.engine.update_component(event.data['target_id'], 'Health', {
            'current_hp': new_hp,
            'max_hp': health['max_hp']
        })
```

### 3. Use Queries to Find Entities
```python
# Find all entities that can be attacked
combatants = engine.query_entities(['Position', 'Health'])

# Find all player characters in a region
players_here = [
    e for e in engine.query_entities(['PlayerCharacter', 'Position'])
    if engine.get_component(e.id, 'Position')['region'] == 'dungeon_entrance'
]

# Find all containers with items
containers_with_items = [
    e for e in engine.query_entities(['Container'])
    if engine.get_relationships(e.id, 'contains', 'from')
]
```

### 4. Leverage Events for Audit Trail
Every state change automatically creates an event. Use this for:
- **Debugging:** "Why did this character die?"
- **Undo/Redo:** Replay or reverse events
- **History:** "Show me all actions this player took"
- **Triggers:** React to state changes

```python
# Get event history for an entity
events = engine.get_events(entity_id=player_id, limit=20)

# See what happened in the last combat
combat_events = engine.get_events(
    event_type='combat.attack',
    since=combat_start_time
)
```

## File Structure for New Systems

```
src/modules/my_system/
├── __init__.py              # Module class with system logic
├── components.py            # Component definitions
├── events.py               # Event definitions
├── relationships.py        # Relationship definitions (if needed)
└── README.md              # Module documentation
```

## When to Create a New System

Create a new system (module) when you have:
1. **New game mechanics** (combat, crafting, magic, etc.)
2. **Cross-cutting behavior** that affects multiple entities
3. **Business rules** that need centralization

Examples:
- `CombatModule` - Attack resolution, damage calculation
- `InventoryModule` - Moving items between containers
- `MagicModule` - Spell casting, mana management
- `DialogueModule` - Conversation trees, NPC responses
- `QuestModule` - Quest tracking, objectives

## Summary

### We Follow Standard ECS ✅
- Entities = IDs
- Components = Pure data
- Systems = Game logic (via modules)
- Engine = Coordinator
- Nodes = Queries

### Our Special Features 🌟
- **Event-driven** instead of game loop
- **Persistent event log** for audit trail
- **Schema validation** for type safety
- **Module system** for extensibility
- **Web-based** not real-time

### Next Steps 🚀
1. Implement more systems as modules (combat, inventory, magic)
2. Add more components (Stats, Skills, Spells, etc.)
3. Build web UI for triggering system actions
4. Create module documentation for community extensions
