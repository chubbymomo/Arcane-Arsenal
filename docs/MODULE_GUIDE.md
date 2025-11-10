# Arcane Arsenal - Module Development Guide

**Purpose**: Guidelines for creating modules that extend Arcane Arsenal with new game systems, components, and features. Focuses on architectural patterns and design principles.

---

## Core Philosophy

### What Modules Are

**Modules are Extensions, Not Modifications**
- Modules add capabilities without changing core
- Core remains game-agnostic and stable
- Multiple modules can coexist (D&D 5e + homebrew)

**Modules Define Domain Concepts**
- Component types (Health, SpellSlots, Inventory)
- Relationship types (owns, equipped_in, member_of)
- Event types (level_up, spell_cast, item_equipped)
- Systems (combat, movement, crafting)

**Modules Are Self-Contained**
- All module code in `src/modules/module_name/`
- Static resources in `src/web/static/modules/module_name/`
- Dependencies declared explicitly
- Can be enabled/disabled per world

---

## Module Responsibilities

### What Modules Should Do

**Define Types**
- Register component types with JSON schemas
- Register relationship types with validation rules
- Register event types with descriptions
- Define clear, unambiguous names

**Implement Systems**
- Query entities by components
- Validate preconditions before mutations
- Mutate state through StateEngine API
- Emit events for all state changes

**Provide UI**
- Component renderers for character sheets
- Web components for complex interactions
- Styles scoped to module components
- Follow progressive enhancement pattern

**React to Events**
- Subscribe to relevant events
- Update derived state
- Trigger side effects (notifications, cascading changes)
- Don't block event emission

### What Modules Should NOT Do

**Don't Modify Core**
- Don't change StateEngine code
- Don't modify core templates
- Don't touch core database tables
- Don't override core components

**Don't Access Database Directly**
- Always use StateEngine API
- Don't write raw SQL
- Don't bypass validation
- Don't create custom storage

**Don't Create Tight Coupling**
- Don't import other modules directly
- Use events for cross-module communication
- Don't assume other modules exist
- Make dependencies explicit

**Don't Store State Outside Database**
- No module-level caching (unless temporary)
- No file-based state
- No global variables with game state
- Database is single source of truth

---

## Module Structure

### Directory Layout

```
src/modules/your_module/
├── __init__.py           # Module class, registration
├── components/
│   ├── health.py         # Component type definitions
│   ├── inventory.py
│   └── stats.py
├── systems/
│   ├── combat.py         # Game logic systems
│   └── movement.py
└── web/
    ├── components.js     # Web components
    └── styles.css        # Module styles

src/web/static/modules/your_module/
├── components.js         # Copied during deployment
└── styles.css            # Copied during deployment
```

### Module Class

**Minimal Module:**
```python
from src.core.module_base import Module

class MyModule(Module):
    @property
    def name(self) -> str:
        return "my_module"

    @property
    def version(self) -> str:
        return "1.0.0"
```

**Full Module:**
```python
class MyModule(Module):
    @property
    def name(self) -> str:
        return "my_module"

    @property
    def version(self) -> str:
        return "1.0.0"

    def register_component_types(self):
        return [HealthComponent, InventoryComponent]

    def register_relationship_types(self):
        return [OwnsRelationship, EquippedInRelationship]

    def register_event_types(self):
        return [LevelUpEvent, ItemEquippedEvent]

    def register_web_resources(self):
        return {
            'scripts': ['/static/modules/my_module/components.js'],
            'styles': ['/static/modules/my_module/styles.css']
        }

    def initialize(self, engine):
        # Subscribe to events
        engine.event_bus.subscribe('item_equipped', self.on_item_equipped)

    def on_item_equipped(self, event):
        # React to events from other systems
        pass
```

---

## Component Type Design

### Design Principles

**Single Responsibility**
- Each component represents one cohesive concept
- Health component: current/max/temp HP
- Inventory component: capacity, items reference
- NOT: CharacterData with everything

**Schema-First**
- Define JSON schema before implementation
- Validate all data against schema
- Version schemas for migrations
- Document all fields

**Immutable Snapshots**
- Components represent state at a point in time
- Don't store methods or behavior
- Computed values go in systems, not components
- Keep serialization simple

### When to Create a Component Type

**Create a Component When:**
- Data logically groups together (HP values, position coordinates)
- Data defines entity capabilities (Inventory enables holding items)
- Data changes together (updating HP often updates temp HP too)
- Data is intrinsic to the entity (stats, description)

**Don't Create a Component When:**
- Data is a relationship to another entity (use relationship)
- Data is temporary UI state (use Alpine.js)
- Data duplicates existing components
- Data is derived from other components (compute on demand)

### Component Granularity

| Too Coarse | Just Right | Too Fine |
|------------|------------|----------|
| CharacterData: name, HP, stats, inventory | Health: current/max/temp HP | CurrentHP: value |
| AllStats: strength, dex, int, wisdom, etc. | Attributes: all ability scores together | Strength: value |

**Guidelines:**
- If you're always querying fields together → one component
- If fields have different update patterns → separate components
- If removing one field makes others meaningless → one component

---

## Relationship Type Design

### Design Principles

**Explicit Naming**
- Use clear, unambiguous verbs: "owns", "located_at", "member_of"
- Avoid synonyms: pick one and stick with it
- Direction should read naturally: "Character owns Item"

**Validation at Type Level**
- Validate from_entity has required components
- Validate to_entity has required components
- Example: "equipped_in" requires from_entity to have Item component

**Metadata for Context**
- Use metadata for relationship-specific data
- Examples: trust_level, equipped_slot, join_date
- Don't duplicate entity data in metadata

### When to Use Relationships

**Use Relationships For:**
- Connections between entities (ownership, location, membership)
- Dynamic associations (can change frequently)
- Graph queries (who knows whom, what's connected)

**Don't Use Relationships For:**
- Entity properties (use components)
- Temporary UI state (use Alpine.js)
- Derived data (compute from existing relationships)

---

## System Design

### System Patterns

**Query → Validate → Mutate → Emit**
1. Query entities with required components
2. Validate preconditions (has enough HP, item exists)
3. Mutate state via StateEngine API
4. Emit event describing what happened

**Example Flow:**
```
1. Query: Get character with Health component
2. Validate: damage <= current_hp + temp_hp
3. Mutate: Update Health component with new values
4. Emit: 'health_changed' event with old/new values
```

**Idempotent Operations**
- Systems should produce same result given same inputs
- Don't rely on external state or randomness (except RNG module)
- Make decisions based on database state
- Predictable for testing and debugging

**Transactional Thinking**
- Group related mutations in transactions
- Roll back on validation failure
- Emit events after successful commit
- Keep transactions short

### Cross-Module Communication

**Use Events, Not Direct Calls**
- Don't import other modules
- Subscribe to relevant events
- Emit events for your module's actions
- Loose coupling via event bus

**Event Patterns:**
```python
# Module A emits event
engine.event_bus.emit(Event(
    event_type='spell_cast',
    entity_id=caster_id,
    data={'spell_name': 'Fireball', 'targets': [target_id]}
))

# Module B reacts to event
def on_spell_cast(self, event):
    # Update visual effects, trigger sound, etc.
    pass
```

---

## UI Integration

### Component Renderers

**Server-Side Rendering:**
- Return HTML string from `get_character_sheet_renderer()`
- Use Jinja-style templating or f-strings
- Escape all user data
- Include HTMX/Alpine attributes for interactivity

**Progressive Enhancement:**
- Start with semantic HTML
- Add HTMX for server interactions
- Add Alpine for client state
- Add WebSocket for real-time updates

**Example Renderer:**
```python
def get_character_sheet_renderer(self, data, engine=None):
    current = data.get('current_hp', 0)
    max_hp = data.get('max_hp', 1)

    return f'''
    <div class="health-display">
        <div class="hp-bar" style="width: {(current/max_hp)*100}%"></div>
        <span>{current} / {max_hp}</span>
    </div>
    '''
```

### Web Components

**When to Create Web Components:**
- Complex, interactive UI (spell lists, skill trees)
- Reusable across contexts (character sheet, DM view)
- Encapsulated behavior (internal state, events)

**When NOT to Create Web Components:**
- Simple displays (use renderers)
- One-off UI (inline HTML)
- Performance-critical (Alpine is faster for simple cases)

**Web Component Guidelines:**
- Clean up event listeners in `disconnectedCallback()`
- Parse attributes in `connectedCallback()`
- Use Alpine inside component HTML for reactivity
- Scope styles to component

---

## Data Modeling Decisions

### Component vs Relationship Decision Tree

```
Is this data about the entity itself?
├─ YES: Is it intrinsic (part of what the entity IS)?
│  ├─ YES: Component
│  └─ NO: Is it a connection to another entity?
│     ├─ YES: Relationship
│     └─ NO: Component (probably state)
└─ NO: Is it a connection to another entity?
   ├─ YES: Relationship
   └─ NO: Derived data or UI state (compute or Alpine)
```

**Examples:**
- "Character has 25 HP" → Component (Health)
- "Character is in Tavern" → Relationship (located_at)
- "Character owns Sword" → Relationship (owns)
- "HP percentage" → Derived (compute from Health component)
- "Inventory panel open" → UI state (Alpine)

### Event Design

**Event Naming:**
- Past tense: "health_changed" not "change_health"
- Specific: "spell_cast" not "action_performed"
- Scoped: "dnd5e_level_up" if game-specific

**Event Data:**
- Include entity_id, actor_id (who caused it)
- Include old/new values for changes
- Include context (spell_name, damage_type)
- Don't include entire entity state (query if needed)

**Event Granularity:**
- One event per atomic change
- Emit separate events for separate concerns
- Example: "hp_changed" + "character_died" not "hp_changed_and_maybe_died"

---

## Module Dependencies

### Declaring Dependencies

**Explicit Dependencies:**
- List required modules in module metadata
- Check for required components/relationships on init
- Fail fast if dependencies missing
- Document dependencies in README

**Optional Dependencies:**
- Check if module is loaded before using features
- Degrade gracefully if not available
- Use events for loose coupling
- Don't assume module order

### Core Module Dependencies

**Modules Can Depend On:**
- Core components (Identity, Position)
- Core relationships (located_at)
- Core events (entity_created, component_added)

**Core Should Not Depend On:**
- Any specific game module
- Optional modules
- Third-party modules

---

## Versioning and Migrations

### Schema Versioning

**Version All Component Schemas:**
- Use semantic versioning (1.0.0, 1.1.0, 2.0.0)
- Increment minor for compatible changes (new optional field)
- Increment major for breaking changes (required field, type change)
- Store schema_version in component_types table

**Migration Strategy:**
- Write migration functions for major versions
- Test migrations on copies of data
- Document breaking changes
- Provide migration tools/scripts

### Backward Compatibility

**Maintain Compatibility When Possible:**
- Add optional fields instead of required
- Deprecate instead of removing
- Support old event formats temporarily
- Version APIs and renderers

**Breaking Changes:**
- Document clearly in CHANGELOG
- Provide migration path
- Bump major version
- Consider dual-read period

---

## Testing Modules

### Test Layers

**Unit Tests:**
- Component schema validation
- Relationship validation rules
- System logic (query → validate → mutate)
- Event emission

**Integration Tests:**
- Module registration
- Component CRUD via StateEngine
- Event handling and propagation
- Cross-module event flow

**UI Tests:**
- Component renderers produce valid HTML
- Web components render correctly
- HTMX endpoints return expected HTML
- Alpine state updates as expected

### Testing Patterns

**Test with StateEngine:**
```python
def test_health_component():
    engine = create_test_engine()
    engine.load_module(MyModule())

    # Create entity with component
    result = engine.create_entity("TestChar")
    entity_id = result.data.id

    result = engine.add_component(
        entity_id,
        "Health",
        {"current_hp": 50, "max_hp": 100}
    )

    assert result.success

    # Verify component exists
    component = engine.get_component(entity_id, "Health")
    assert component.data['current_hp'] == 50
```

**Test Events:**
```python
def test_health_event_emission():
    engine = create_test_engine()
    events_received = []

    engine.event_bus.subscribe('health_changed',
                                lambda e: events_received.append(e))

    # Trigger health change
    system.damage_entity(entity_id, 10)

    assert len(events_received) == 1
    assert events_received[0].data['damage'] == 10
```

---

## Common Patterns

### Cached Derived State

**Pattern: Maintain Computed Values**
- Listen to relevant events
- Recalculate and store in component
- Example: Total XP from XP events

**When to Use:**
- Expensive calculations queried frequently
- Aggregate values (total XP, item count)
- Historical summaries

**When NOT to Use:**
- Simple calculations (HP percentage)
- Rarely queried values
- Values that change with every update

### Conditional Component Loading

**Pattern: Optional Components**
- Check if component exists before using
- Graceful degradation if missing
- Example: Spellbook only on spellcasters

**Implementation:**
```python
health = engine.get_component(entity_id, "Health")
if health:
    # Character can take damage
    system.damage(entity_id, amount)
else:
    # No health component, skip or warn
    pass
```

### Multi-Component Queries

**Pattern: Find Entities with Multiple Components**
- Query for entities with all required components
- Example: All living characters in location

**Implementation:**
```python
# Characters with Health AND Position in region
candidates = engine.query_entities(
    component_types=["Health", "Position"],
    filters={"Position.region": "tavern"}
)
```

---

## Anti-Patterns

### ❌ God Modules

**Bad: Module that does everything**
- One module for all D&D 5e (combat, spells, items, leveling)
- Too large, hard to test, tight coupling

**Good: Focused modules**
- dnd5e_core: Attributes, Skills
- dnd5e_combat: Health, AC, attacks
- dnd5e_magic: Spells, spell slots
- dnd5e_items: Equipment, inventory

### ❌ Component Inheritance

**Bad: Creating component hierarchies**
```python
class BaseWeapon(ComponentTypeDefinition): ...
class Sword(BaseWeapon): ...
class Longsword(Sword): ...
```

**Good: Composition with tags**
```python
class Weapon(ComponentTypeDefinition):
    schema = {
        "type": "object",
        "properties": {
            "weapon_type": {"enum": ["sword", "axe", "bow"]},
            "subtype": {"type": "string"},  # "longsword", etc.
        }
    }
```

### ❌ Storing Entity IDs in Components

**Bad: Component contains entity references**
```python
Inventory: {"items": ["item_1", "item_2", "item_3"]}
```

**Good: Use relationships**
```python
# Create relationships instead
Character --owns--> Item1
Character --owns--> Item2
Character --owns--> Item3
```

### ❌ Bypassing Validation

**Bad: Direct database writes**
```python
# Don't do this!
storage.execute("UPDATE components SET data = '...' WHERE ...")
```

**Good: Use StateEngine API**
```python
engine.update_component(entity_id, "Health", new_data)
```

---

## Module Publishing

### Distribution

**As Part of Arcane Arsenal:**
- Place in `src/modules/module_name/`
- Include in default installation
- Maintain with core

**As Third-Party Package:**
- Publish to PyPI
- Install via `pip install arcane-arsenal-module-name`
- Load dynamically from entry point

**As World-Specific:**
- Place in `worlds/my_world/modules/`
- Only loaded for that world
- Experimental or campaign-specific

### Documentation

**Module README Should Include:**
- What game system/features it provides
- Component types and schemas
- Relationship types
- Event types
- Dependencies (other modules, versions)
- Installation instructions
- Example usage

### Configuration

**World Configuration:**
```json
{
  "world_name": "My Campaign",
  "modules": [
    "core_components",
    "dnd5e_core",
    "dnd5e_combat",
    "my_homebrew_module"
  ]
}
```

**Module Load Order:**
- Core modules first
- Dependencies before dependents
- Game system modules
- Campaign-specific modules

---

## Design Decision Framework

### When Creating a Module

**1. Define Scope**
- What domain does this module cover?
- What components/relationships/events does it need?
- What systems does it implement?

**2. Identify Dependencies**
- What core components does it require?
- Does it depend on other modules?
- Can it stand alone?

**3. Design Components**
- List all component types
- Define JSON schemas
- Version schemas from the start
- Consider migrations

**4. Design Relationships**
- List all relationship types
- Define validation rules
- Document directionality
- Consider queries

**5. Design Events**
- List all event types
- Define event data structures
- Plan event flow (what triggers what)
- Consider event handlers

**6. Implement Systems**
- One system at a time
- Query → Validate → Mutate → Emit
- Test thoroughly
- Document preconditions

**7. Build UI**
- Component renderers first
- Web components for complex UI
- Progressive enhancement
- Test accessibility

---

## Checklist

Before publishing a module:

- [ ] Module class defines name, version
- [ ] All component types registered with schemas
- [ ] All relationship types registered with validation
- [ ] All event types registered with descriptions
- [ ] Systems use StateEngine API (no direct DB access)
- [ ] Events emitted for all state changes
- [ ] Component renderers escape user data
- [ ] Web components clean up in disconnectedCallback
- [ ] UI follows progressive enhancement
- [ ] Tests cover component validation, systems, events
- [ ] Dependencies documented
- [ ] README includes schemas and examples
- [ ] Migration path for breaking changes
- [ ] No tight coupling to other modules

---

## Summary

**Modules extend Arcane Arsenal by:**
- Defining domain-specific components, relationships, events
- Implementing game logic systems
- Providing UI renderers and components
- Reacting to events

**When creating modules:**
- Keep scope focused
- Use composition over inheritance
- Store state in database via StateEngine
- Emit events for all changes
- Validate all inputs
- Test thoroughly
- Document clearly

**Always ask:**
- Is this the right abstraction (component/relationship/event)?
- Does this belong in this module (scope creep)?
- Are dependencies explicit and minimal?
- Is state in the database?
- Will this work with other modules?

---

**Last Updated**: 2025-11-08
