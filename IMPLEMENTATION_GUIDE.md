# Arcane Arsenal - Implementation Guide

**Purpose**: This document defines strict guidelines for implementing features in Arcane Arsenal. It focuses on architectural patterns, design principles, and decision-making frameworks rather than specific code implementations.

---

## Core Philosophy

### Primary Goals
1. **State Truth**: The database is the single source of truth for world state
2. **AI Compatibility**: All data must be queryable, explicit, and typed to prevent AI hallucination
3. **Modularity**: New features extend the system without modifying core
4. **Auditability**: Every state change is traceable through events

### Architectural Principles

**Composition over Inheritance**
- Build complex entities by combining simple components
- Never create entity subclasses or hierarchies
- A dragon and a merchant differ by components, not classes

**Explicit over Implicit**
- Name all types in registries (component_types, relationship_types, event_types)
- Avoid magic strings or undocumented states
- Relationships are named edges, not inferred connections

**Data in Database, Logic in Code**
- Database enforces foreign keys and stores data
- Python enforces business rules and validation
- Schema changes are rare; logic changes are frequent

**Event-Driven State Changes**
- All mutations emit events
- Events are append-only and immutable
- Events enable time-travel debugging and audit trails

---

## Entity Component System (ECS)

### Entity Design

**What is an Entity?**
- A unique identifier with a name
- A container for components
- No behavior or data of its own

**When to Create an Entity**
- Anything that can be referenced or queried (characters, items, locations, factions, quests)
- Abstract concepts that have state (a prophecy, a rumor, a spell effect)
- NOT for purely UI state or temporary data

**Entity Lifecycle**
- Created with minimal data (ID and name)
- Enhanced by adding components
- Soft-deleted to preserve history
- Restorable if needed

### Component Design

**What is a Component?**
- Typed data attached to an entity
- Pure data, no methods
- Validated against a JSON schema

**When to Create a Component Type**
- Data that logically groups together (Health: current/max, Position: x/y/z)
- Data that defines capabilities (an entity with Inventory can hold items)
- Domain-specific attributes (DnD5eStats, ModernInventory, SpellSlots)

**Component Granularity**
- **Too coarse**: Storing unrelated data together (Health + Position + Name)
- **Too fine**: Each field as its own component (CurrentHP, MaxHP, TempHP)
- **Just right**: Cohesive data that changes together (Health with all HP fields)

**Component Ownership**
- Components belong to modules
- Core modules provide universal components (Identity, Position)
- Game-specific modules provide domain components (DnD5eStats, CyberpunkSkills)

### Relationship Design

**What is a Relationship?**
- A named, directed edge between two entities
- Has a type registered in relationship_types
- Can carry metadata (timestamps, strength, context)

**When to Use Relationships**
- Explicit connections: "knows", "located_at", "owns", "member_of"
- Dynamic associations: party membership, item ownership, spatial containment
- Social graphs: trust, rivalry, loyalty

**Relationship Direction**
- FROM → TO should read naturally: "Theron" located_at "Tavern"
- Direction matters: "A knows B" ≠ "B knows A" (unless you create both)
- Queries can find both incoming and outgoing edges

**Relationships vs Components**
- **Component**: Intrinsic property (Health is part of a character)
- **Relationship**: Extrinsic connection (Character is in Location)

### System Patterns

**What is a System?**
- Logic that queries entities by components and performs operations
- Examples: Combat system, movement system, inventory system
- Lives in modules, not in core

**System Implementation**
- Query for entities with required components
- Validate preconditions
- Mutate state through StateEngine API
- Emit events for state changes
- Return results (success/failure)

**System Coordination**
- Systems react to events from other systems
- Use event bus for decoupled communication
- Avoid direct system-to-system calls

---

## Event-Driven Architecture

### Event Philosophy

**Events are History**
- Every event is a fact that happened at a specific time
- Events are never modified or deleted
- Current state is the result of applying all events

**Events are Not Commands**
- Event: "character.health_changed" (past tense, fact)
- Not: "change_character_health" (imperative, command)

### Event Design

**When to Emit Events**
- Every entity create/update/delete
- Every component add/update/remove
- Every relationship create/delete
- Domain-specific state changes (combat started, level up, quest completed)

**Event Data Structure**
- Type: Registered in event_types table
- Entity ID: Primary entity affected (can be null for world events)
- Actor ID: Who/what caused this event (player, NPC, system)
- Data: Context-specific payload (old/new values, parameters)
- Timestamp: When it happened

**Event Granularity**
- Emit one event per atomic state change
- Don't emit "mega events" that bundle unrelated changes
- Group related micro-changes into a transaction, but still emit individual events

### Event Handling

**Reactive Systems**
- Modules subscribe to events via event bus
- Handle events asynchronously where possible
- Don't block event emission with heavy processing

**Event Patterns**
- **Audit Trail**: Log who did what when
- **Replication**: Send events to clients for real-time updates
- **Derived State**: Maintain cached aggregates (XP total, item count)
- **Time Travel**: Replay events to reconstruct past state

---

## Module System

### Module Responsibilities

**What Modules Do**
- Define component types with schemas
- Define relationship types with validation
- Define event types with descriptions
- Implement systems (game logic)
- React to events from other modules

**What Modules Don't Do**
- Modify core engine code
- Access database directly (use StateEngine API)
- Create circular dependencies with other modules
- Store state outside the database

### Module Lifecycle

**Registration Phase**
- Module registers its types with the engine
- Types are inserted into registry tables
- Duplicate registrations are errors

**Initialization Phase**
- Module receives reference to StateEngine
- Module can query existing state
- Module subscribes to events

**Runtime Phase**
- Module reacts to events
- Module provides API for its systems
- Module validates data against its schemas

### Module Boundaries

**Core Modules**
- Universally applicable (Identity, Position, Health)
- Minimal assumptions about game system
- Owned by the Arcane Arsenal project

**Game System Modules**
- Domain-specific (DnD5e, Pathfinder, Cyberpunk)
- Depend on core modules
- Can be third-party

**Campaign Modules**
- Specific to a world/campaign
- Can be throwaway or experimental
- Might not be reusable

---

## Data Modeling Guidelines

### Choosing Component Types

**Decision Framework**
1. Is this data intrinsic to the entity? → Component
2. Does it define what the entity **is**? → Component
3. Does it describe the entity's internal state? → Component

**Examples**
- Health: Component (intrinsic property)
- Name: Part of Entity (core identifier)
- Location: Relationship (extrinsic connection)

### Choosing Relationships

**Decision Framework**
1. Does this describe a connection to another entity? → Relationship
2. Can this connection change without changing the entities themselves? → Relationship
3. Is this a graph edge? → Relationship

**Examples**
- "Character is in Location": located_at relationship
- "Character owns Item": owns relationship
- "Character's HP": Health component (not a relationship)

### Avoiding Anti-Patterns

**Don't Store Entity IDs in Components**
- ❌ Inventory component: `{"item_ids": ["item_1", "item_2"]}`
- ✅ Relationships: Character --owns--> Item

**Don't Use Relationships for Properties**
- ❌ Character --has_hp--> HealthValue entity
- ✅ Health component: `{"current": 25, "max": 30}`

**Don't Duplicate Data Across Components**
- ❌ Identity: `{"name": "Theron"}` + Position: `{"entity_name": "Theron"}`
- ✅ Single source per fact: name in Entity, position in Position component

---

## Query & Context Patterns

### Query Design

**Query by Component Type**
- "Find all entities with Health component" → Combat targets
- "Find all entities with Position in region X" → Nearby characters

**Query by Relationships**
- "Find all entities A --located_at--> B" → Who is in location B?
- "Find all entities A <--owns-- B" → Who owns item B?

**Composite Queries**
- Combine component and relationship filters
- Example: "Characters in tavern with Health < 50%"

**Full-Text Search**
- Use for AI natural language queries
- Searches across component data JSON
- Returns entities for refinement

### AI Context Generation

**Context Principles**
- Include only relevant data (focus entity + nearby + related)
- Be explicit about distances, relationships, states
- Provide available actions based on components
- Don't infer or invent data

**Context Structure**
- Focus Entity: Full entity with all components
- Nearby Entities: Based on Position component queries
- Relationships: All edges touching focus entity
- Recent Events: Time-windowed event history
- Available Actions: Computed from components and rules

**Context Size**
- Limit to prevent token overflow
- Prioritize by relevance (distance, recency, importance)
- Paginate or summarize if needed

---

## When to Use What

### Entity vs Component vs Relationship

| Scenario | Solution |
|----------|----------|
| Representing a character, item, location | Entity |
| Storing character's HP, stats, inventory capacity | Component |
| Character is in a location | Relationship (located_at) |
| Item is owned by character | Relationship (owns) |
| Character's description | Component (Identity) |
| Character knows another character | Relationship (knows) |

### Component vs Metadata

| Data Type | Storage |
|-----------|---------|
| Entity's core properties | Component |
| Relationship context (trust level, since date) | Relationship metadata |
| Event context (old value, new value) | Event data |
| Temporary UI state | Not persisted |

### Event vs State

| Information | Storage |
|-------------|---------|
| Current HP value | Component data |
| Fact that HP changed | Event |
| Who changed HP | Event actor_id |
| What HP changed from/to | Event data |

---

## Implementation Practices

### Validation Strategy

**Where to Validate**
- Component data: Against JSON schema at add/update time
- Relationship: In relationship type definition (validate from/to entities)
- Events: Trust events from internal systems, validate from external sources
- API inputs: At the boundary (web forms, CLI commands)

**Validation Flow**
1. Parse input data
2. Check type exists in registry
3. Validate against schema
4. Check business rules (entity exists, component not duplicate, etc.)
5. Perform operation
6. Emit event

### Error Handling

**Use Result Objects**
- Success: `Result.ok(data)`
- Failure: `Result.fail(error_message, error_code)`
- Don't raise exceptions for expected failures (entity not found)
- Do raise exceptions for programmer errors (invalid types)

**Error Codes**
- ENTITY_NOT_FOUND
- COMPONENT_TYPE_NOT_REGISTERED
- VALIDATION_FAILED
- DUPLICATE_COMPONENT
- RELATIONSHIP_INVALID

### Transaction Patterns

**When to Use Transactions**
- Multi-step operations that must be atomic
- Operations that read-then-write (check precondition, apply change)
- Batch operations (creating entity + components + relationships)

**Transaction Scope**
- Keep transactions short
- Don't emit side effects (network calls) inside transactions
- Emit events after transaction commits

### Testing Approach

**Unit Tests**
- Test each component type's schema validation
- Test StateEngine methods in isolation
- Mock storage layer

**Integration Tests**
- Test full workflows (create entity → add components → query)
- Use real SQLite database (in-memory for speed)
- Test event emission and handling

**Module Tests**
- Test module registration
- Test module systems with mock data
- Test event reactions

---

## Design Decision Framework

### When Adding a Feature

**1. Identify the Domain Concept**
- What are you representing? (entity, component, relationship?)
- Is this a new type or a new instance?

**2. Choose the Right Abstraction**
- Intrinsic property → Component
- Connection → Relationship
- Historical fact → Event
- Query logic → System

**3. Define the Contract**
- What data does this need? (JSON schema)
- What invariants must hold? (validation rules)
- What events does this emit?

**4. Implement Minimally**
- Register type
- Implement validation
- Add CRUD operations
- Emit events
- Write tests

**5. Iterate on Usage**
- Build systems that use the type
- Refine schema based on real usage
- Add convenience methods if needed

### When Refactoring

**Signs You Need to Refactor**
- Duplicate data across components
- Complex component schemas that are really multiple concepts
- Business logic scattered across multiple modules
- Validation logic inconsistent or missing

**Refactoring Strategy**
- Write tests for current behavior
- Create new types with clear contracts
- Migrate data with a script
- Update version numbers
- Deprecate old types gracefully

---

## Consistency Checklist

Before merging any feature, ensure:

- [ ] All new types are registered in appropriate tables
- [ ] JSON schemas are defined and validated
- [ ] State changes emit events with clear types
- [ ] Events are past-tense, factual names
- [ ] Error cases return Result.fail() with error codes
- [ ] Queries use indexes (entity_id, component_type, relationship_type)
- [ ] Soft deletes are used (never hard delete entities/components)
- [ ] Tests cover happy path and error cases
- [ ] AI context generation includes new components/relationships
- [ ] Documentation explains when to use this feature

---

## Anti-Patterns to Avoid

❌ **Entity Inheritance**
- Don't create "Character" and "NPC" subclasses
- Use PlayerCharacter component to differentiate

❌ **God Components**
- Don't create a "CharacterData" component with everything
- Split into Health, Stats, Inventory, etc.

❌ **Implicit Relationships**
- Don't infer "A knows B" from message history
- Create explicit "knows" relationship

❌ **Validation in Database**
- Don't use CHECK constraints for business rules
- Validate in Python before writing

❌ **Mutable Events**
- Don't update event data after emission
- Emit a new event if state changes again

❌ **Stateful Systems**
- Don't store state in system classes
- Query current state from database each time

❌ **Circular Module Dependencies**
- Don't have Module A import Module B import Module A
- Use events for cross-module communication

---

## Summary

**Arcane Arsenal is:**
- An ECS-based state manager for RPG worlds
- Event-driven and audit-ready
- Modular and extensible
- AI-friendly through explicit, typed data

**When implementing features:**
- Start with data model (entity/component/relationship)
- Define types and schemas clearly
- Emit events for all state changes
- Write systems that query and mutate state
- Test thoroughly
- Think about AI context generation

**Always ask:**
- Is this the right abstraction?
- Is this data explicit and typed?
- Will an AI understand this without guessing?
- Can this be queried efficiently?
- Is history preserved?

---

**Last Updated**: 2025-11-08
