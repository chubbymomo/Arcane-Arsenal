# Arcane Arsenal: Philosophy Distillation & Codebase Review Plan

**Created**: 2025-11-10
**Purpose**: Distilled philosophy from documentation + comprehensive 10-phase review plan

---

## Philosophy Distillation

### Core Architectural Principles

#### 1. **State Truth & Explicitness**
- **Single Source of Truth**: SQLite database holds ALL authoritative game state
- **No Implicit Behavior**: Everything must be explicitly defined and registered
- **No Magic Strings**: All types (components, relationships, events) registered in tables
- **Queryable Reality**: AI and systems can only act on what's explicitly in the database

#### 2. **Entity Component System (ECS)**
- **Composition over Inheritance**: Entities composed of components, never subclassed
- **Separation of Data & Logic**: Components = pure data, Systems = logic that acts on data
- **Components Define Capabilities**: Having Inventory component means entity CAN hold items
- **Relationships are Explicit Edges**: Named, directed connections ("located_at", "owns", "knows")

#### 3. **Event-Driven Architecture**
- **Immutable History**: Events are append-only facts, never modified
- **Past Tense Naming**: "health_changed" not "change_health" (facts, not commands)
- **Auditability**: Every state change traceable through event log
- **Event Bus**: Decoupled cross-module communication via pub/sub

#### 4. **Validation & Safety**
- **Validation in Code, Not Database**: Python enforces business rules, DB enforces foreign keys
- **Schema-First Components**: JSON schemas define and validate all component data
- **Soft Deletes**: Preserve history, maintain referential integrity, support undo
- **Result Objects**: No exceptions for expected failures, explicit success/fail states

#### 5. **Modularity & Extensibility**
- **Modules Extend, Never Modify Core**: Core remains game-agnostic and stable
- **Modules are Self-Contained**: All code in module directory, explicit dependencies
- **Type Registration**: Modules register their component/relationship/event types
- **Event-Based Communication**: Modules communicate via events, not direct calls

#### 6. **Frontend Progressive Enhancement**
- **Server-Rendered Foundation**: HTML first, JavaScript enhances
- **Technology Separation**: HTMX (server), Alpine (client state), Socket.IO (real-time)
- **State Lives in Database**: Client state is ephemeral UI, never game state
- **Works Without JavaScript**: Basic functionality degrades gracefully

#### 7. **AI Compatibility**
- **Typed & Structured**: All data has explicit schemas, preventing hallucination
- **Contextual Queries**: AI receives focused, relevant data
- **Available Actions**: Systems compute what's possible based on components
- **No Guessing**: If data doesn't exist in DB, it doesn't exist in world

---

## Anti-Patterns (Critical to Avoid)

1. ❌ **Entity Inheritance** - Never subclass entities (use components)
2. ❌ **God Components** - Don't create "CharacterData" with everything
3. ❌ **IDs in Components** - Never store entity IDs in component data (use relationships)
4. ❌ **Implicit Relationships** - Don't infer connections (create explicit relationships)
5. ❌ **Mutable Events** - Never modify events after emission
6. ❌ **Stateful Systems** - Systems query DB each time, don't cache state
7. ❌ **Circular Module Dependencies** - Use events for cross-module communication
8. ❌ **Client Game State** - Never store authoritative state in Alpine/JavaScript
9. ❌ **Direct Database Access** - Always use StateEngine API
10. ❌ **Validation in Database** - Validate in Python, not SQL CHECK constraints

---

## 10-Phase Codebase Review Plan

### Phase Overview

| Phase | Scope | Duration | Priority |
|-------|-------|----------|----------|
| 1. Core Foundation | `src/core/` | 2-3 days | CRITICAL |
| 2. Module System | `src/modules/*/` | 2-3 days | CRITICAL |
| 3. Component Design | All component types | 1-2 days | HIGH |
| 4. Relationship Graph | Relationship types & patterns | 1-2 days | HIGH |
| 5. Event System | Event emission & handling | 1-2 days | HIGH |
| 6. Frontend Architecture | `src/web/` | 1-2 days | MEDIUM |
| 7. Cross-Cutting Concerns | Error handling, transactions, AI context | 1-2 days | MEDIUM |
| 8. Testing & Documentation | Tests, docs alignment | 2-3 days | MEDIUM |
| 9. Performance | Query optimization, scalability | 1-2 days | LOW |
| 10. Security | Input validation, permissions | 1-2 days | MEDIUM |

**Total Estimated Time**: 2-3 weeks

---

## PHASE 1: Core Foundation Review

**Files**: `src/core/*.py` (state_engine, storage, models, event_bus, result)

### Checklist

#### State Truth
- [ ] StateEngine is only API for database access
- [ ] All operations emit events
- [ ] Soft deletes used everywhere
- [ ] No business logic in storage layer

#### Explicit over Implicit
- [ ] All types checked against registries
- [ ] No magic strings
- [ ] Clear error messages with codes

#### Validation in Code
- [ ] Component data validated against schemas
- [ ] Relationship validation in Python, not SQL
- [ ] Result objects used, not exceptions

#### Event-Driven
- [ ] Events immutable after emission
- [ ] Events named in past tense
- [ ] Event bus is pub/sub

### Common Violations
- Direct SQL outside storage.py
- Hard deletes instead of soft deletes
- Exceptions for expected errors
- State mutations without events
- Business logic in storage layer

### Ripple Effects
| Change | Affected Areas |
|--------|---------------|
| StateEngine signature | All modules, web routes, CLI |
| Event structure | All event handlers |
| Storage interface | StateEngine |
| Result object | All error handling |

### Mitigation
1. Document API changes before making them
2. Search codebase: `grep -r "function_name" src/`
3. Create deprecation path
4. Update all call sites
5. Run full test suite

---

## PHASE 2: Module System Architecture

**Files**: `src/modules/*/` (all modules)

### Per-Module Checklist

#### Modularity
- [ ] No direct imports of other modules
- [ ] Dependencies declared explicitly
- [ ] Can be enabled/disabled independently
- [ ] No modifications to core

#### Type Registration
- [ ] Component types have JSON schemas
- [ ] Relationship types validated
- [ ] Event types registered with descriptions
- [ ] Schema versions tracked

#### Event Communication
- [ ] Cross-module communication via events only
- [ ] Event handlers don't block
- [ ] Events provide context, not full state

#### Data Modeling
- [ ] No entity IDs in component data
- [ ] Components are intrinsic properties
- [ ] Relationships are extrinsic connections
- [ ] No duplicate data across components

### Component Type Checks
For EACH component:
- [ ] Valid JSON schema
- [ ] Schema validates correctly
- [ ] No entity IDs in data fields
- [ ] Renderer escapes user data
- [ ] Appropriate granularity

### System Checks
For EACH system:
- [ ] Query → Validate → Mutate → Emit pattern
- [ ] Uses StateEngine API only
- [ ] Returns Result objects
- [ ] Idempotent where possible

### Ripple Effects

**Component Schema Changes**:
- **Add optional field** → Backwards compatible
- **Add required field** → Migration script, version bump
- **Remove field** → Check all readers, deprecation period
- **Rename field** → Dual-read period

**Relationship Type Changes**:
- **Add type** → Update systems, check queries
- **Remove type** → Check all create calls
- **Change validation** → May break existing relationships

### Mitigation
1. Before schema change: `grep -r "ComponentName" src/`
2. Plan migration script for breaking changes
3. Check template renderers
4. Update systems that query this component

---

## PHASE 3: Component Type Consistency

**Scope**: Deep dive into component design quality

### Component Design Checklist

For EACH component type:

#### Single Responsibility
- [ ] Represents one cohesive concept
- [ ] Fields logically belong together
- [ ] Not a "god component"

#### Schema Quality
- [ ] All fields documented
- [ ] Appropriate types
- [ ] Required vs optional clear
- [ ] Enums used where appropriate
- [ ] No entity_id fields

#### Data Modeling
- [ ] No relationships disguised as fields
- [ ] No duplicate data
- [ ] Computed values not stored
- [ ] Appropriate granularity

#### Frontend Integration
- [ ] Renderer escapes all user data
- [ ] Progressive enhancement
- [ ] HTMX/Alpine/Socket.IO appropriate
- [ ] Accessibility considered

### Specific Anti-Pattern Examples

**Inventory Component**:
```python
# ❌ BAD - storing entity IDs
{"items": ["item_1", "item_2"]}

# ✅ GOOD - use relationships
# Character --owns--> Item
```

**Position Component**:
```python
# ❌ BAD - duplicate data
{"x": 100, "y": 200, "entity_name": "Theron"}

# ✅ GOOD - position only
{"x": 100, "y": 200, "region": "tavern"}
```

### Refactoring Impact

**Splitting a god component**:
1. Create new component types with proper schemas
2. Write migration script: old → new
3. Update all queries
4. Update renderers
5. Deprecate old component

---

## PHASE 4: Relationship & Graph Structure

**Scope**: Relationship types and graph query patterns

### Relationship Design Checks

For EACH relationship type:

#### Naming
- [ ] Clear, unambiguous verb
- [ ] Direction reads naturally
- [ ] Consistent with similar relationships
- [ ] No synonyms (pick one: "contains" not "has"/"holds")

#### Validation
- [ ] from_entity validation implemented
- [ ] to_entity validation implemented
- [ ] Metadata schema if needed

#### Usage
- [ ] Used correctly throughout
- [ ] No components doing relationship's job
- [ ] Query patterns efficient

### Anti-Patterns

```python
# ❌ BAD - component for relationship
Inventory: {"items": [...]}

# ✅ GOOD - explicit relationship
Character --owns--> Item

# ❌ BAD - unclear direction
knows(A, B)

# ✅ GOOD - directed edge
A --knows--> B
```

### Graph Query Patterns

1. **Spatial Queries**
   - [ ] Uses `located_at` relationships
   - [ ] Efficient indexes

2. **Ownership Queries**
   - [ ] Outgoing `owns` for "what does X own?"
   - [ ] Incoming `owns` for "who owns Y?"

### Ripple Effects

**Renaming relationship type**:
- All create_relationship calls
- All queries
- UI displays
- Migration script

**Changing direction**:
- MAJOR BREAKING CHANGE
- All queries affected
- Complete rewrite needed

### Mitigation
1. Search: `grep -r 'create_relationship.*"type"'`
2. Search: `grep -r 'get_relationships.*"type"'`
3. Check templates
4. Migration script
5. Test on copy first

---

## PHASE 5: Event System & Auditability

**Scope**: Event emission, handling, historical integrity

### Event Architecture Checks

#### Event Emission
- [ ] Every state change emits event
- [ ] Events emitted AFTER successful mutation
- [ ] Events include old/new values
- [ ] Clear, descriptive data

#### Event Naming
- [ ] Past tense
- [ ] Specific (not generic)
- [ ] Scoped by domain if needed

#### Event Immutability
- [ ] Never modified after emission
- [ ] No UPDATE on events table
- [ ] Append-only log

#### Event Handling
- [ ] Handlers don't block emission
- [ ] Handlers are idempotent
- [ ] Don't assume event order

### Event Handler Review

For EACH subscription:
- [ ] Doesn't modify event data
- [ ] Doesn't block
- [ ] Handles malformed events gracefully
- [ ] Idempotent

### Ripple Effects

**Event structure changes**:
- All handlers affected
- Frontend displays affected
- Historical events have old structure
- Need versioning strategy

### Mitigation
1. Find handlers: `grep -r 'event_bus.subscribe'`
2. Find socket emits: `grep -r 'socketio.emit'`
3. Check frontend: `grep -r "socket.on"`
4. Event versioning: add version field, handle multiple formats

---

## PHASE 6: Frontend Architecture

**Scope**: `src/web/` (server, templates, static, Socket.IO)

### Progressive Enhancement Checks

For EACH page/feature:

#### Level 1: HTML-Only
- [ ] Forms submit via POST
- [ ] Works without JavaScript
- [ ] Semantic HTML
- [ ] Accessible

#### Level 2: HTMX
- [ ] Partial updates
- [ ] Graceful degradation
- [ ] Loading states
- [ ] Error handling

#### Level 3: Alpine.js
- [ ] Client state scoped
- [ ] No game state in Alpine
- [ ] Computed values, not stored
- [ ] Clean on reload

#### Level 4: WebSocket
- [ ] Real-time features only
- [ ] Reconnection handled
- [ ] Idempotent handlers
- [ ] Fallback if disconnected

### Technology Separation

**HTMX**: fetch data, submit forms, partial updates
**Alpine**: toggles, animations, form validation preview
**Socket.IO**: multiplayer sync, live updates, broadcasts

### Security Checks

**User Data Escaping**:
- [ ] All user input escaped in Jinja: `{{ data | e }}`
- [ ] Component renderers use `markupsafe.escape()`
- [ ] No raw HTML without escaping

**WebSocket Validation**:
- [ ] All messages validated
- [ ] Entity ownership checked
- [ ] Permissions enforced
- [ ] Rate limiting considered

### Anti-Patterns

```html
<!-- ❌ BAD - HTMX and Alpine fighting -->
<div x-data="{ hp: 50 }">
    <div hx-get="/api/hp" hx-swap="innerHTML">
        <span x-text="hp"></span>
    </div>
</div>

<!-- ✅ GOOD - Choose one -->
<div x-data="{ hp: 50 }" x-init="socket.on('hp_updated', d => hp = d.hp)">
    <span x-text="hp"></span>
</div>
```

### Mitigation
1. Test renderers with malicious input
2. Test with multiple connected clients
3. Search: `grep -r "hx-get" src/web/templates/`
4. Verify escaping maintained

---

## PHASE 7: Cross-Cutting Concerns

**Scope**: Patterns that span multiple layers

### 1. Error Handling Consistency

**Result Object Pattern**:
- [ ] StateEngine methods return Result
- [ ] Success: Result.ok(data)
- [ ] Failure: Result.fail(message, code)
- [ ] Error codes consistent
- [ ] No exceptions for expected failures

**Error Propagation**:
- [ ] Errors bubble to API boundary
- [ ] Web routes handle Results
- [ ] CLI displays errors clearly
- [ ] Frontend shows messages

### 2. Transaction Consistency

**Transaction Usage**:
- [ ] Multi-step operations use transactions
- [ ] Read-then-write uses transactions
- [ ] Transactions are short
- [ ] Events emitted after commit
- [ ] No side effects inside

### 3. AI Context Generation

**Context Quality**:
- [ ] Focuses on relevant entities
- [ ] Includes nearby (based on Position)
- [ ] Includes relationships
- [ ] Includes recent events
- [ ] Computes available actions

**Data Explicitness**:
- [ ] No inferred relationships
- [ ] No hallucinated properties
- [ ] All data backed by database

### 4. Multiplayer Synchronization

**Room Management**:
- [ ] Join world rooms
- [ ] Join entity rooms
- [ ] Leave on disconnect
- [ ] Re-join on reconnect

**Event Broadcasting**:
- [ ] State changes broadcast
- [ ] Events include context
- [ ] Idempotent client handling
- [ ] Handles duplicates/out-of-order

### 5. Module Dependencies

**Declaration**:
- [ ] Required modules documented
- [ ] Optional modules handled gracefully
- [ ] Load order respected
- [ ] Circular dependencies prevented

**Communication**:
- [ ] Events used, not direct calls
- [ ] No tight coupling
- [ ] Modules can be disabled

---

## PHASE 8: Testing & Documentation Alignment

**Scope**: Verify implementation matches documentation

### Documentation Consistency

For EACH principle in guides:
- [ ] Find examples in codebase
- [ ] Verify pattern followed
- [ ] Document exceptions with reasons
- [ ] Update guide if practice evolved

For EACH anti-pattern:
- [ ] Search codebase for violations
- [ ] Create issues
- [ ] Refactor or document why needed

### Test Coverage

**Core Tests**:
- [ ] StateEngine CRUD
- [ ] Event emission
- [ ] Transaction behavior
- [ ] Validation logic

**Module Tests**:
- [ ] Component schema validation
- [ ] Relationship validation
- [ ] System logic
- [ ] Event handlers

**Integration Tests**:
- [ ] Full workflows
- [ ] Cross-module event flow
- [ ] AI context generation
- [ ] Multiplayer sync

**Frontend Tests**:
- [ ] Progressive enhancement
- [ ] WebSocket communication
- [ ] Alpine state
- [ ] HTMX updates

### Documentation Gaps
- [ ] Undocumented component types
- [ ] Undocumented relationship types
- [ ] Undocumented event types
- [ ] Missing API docs
- [ ] Missing module READMEs

### Commands
```bash
# Run tests
pytest tests/ -v

# Coverage report
pytest --cov=src tests/

# Generate coverage HTML
pytest --cov=src --cov-report=html tests/
```

---

## PHASE 9: Performance & Scalability

**Scope**: Query performance, index usage, bottlenecks

### Database Performance

**Index Coverage**:
- [ ] Components: (entity_id, component_type)
- [ ] Relationships: (from_entity, type), (to_entity, type)
- [ ] Events: (entity_id), (event_type), (timestamp)
- [ ] Full-text search: components_fts

**Query Patterns**:
- [ ] N+1 queries identified and fixed
- [ ] Batch operations where appropriate
- [ ] Avoid SELECT * in hot paths
- [ ] Use indexes for all queries

**Transaction Length**:
- [ ] Short transactions
- [ ] No long operations in transactions
- [ ] Minimal lock contention

### Frontend Performance

**Asset Loading**:
- [ ] CDN for libraries
- [ ] Minimal custom JavaScript
- [ ] CSS bundled appropriately
- [ ] No blocking scripts

**Real-time Overhead**:
- [ ] WebSocket only when needed
- [ ] Event payloads minimal
- [ ] Throttling/debouncing appropriate
- [ ] Reconnection handled gracefully

### Scalability

**Single World**:
- [ ] Handles 1000+ entities
- [ ] Handles 10+ simultaneous users
- [ ] Event log grows appropriately
- [ ] Queries remain fast

**Multiple Worlds**:
- [ ] Each world isolated
- [ ] No shared state
- [ ] World switching efficient

---

## PHASE 10: Security & Data Integrity

**Scope**: Security vulnerabilities, data validation, permissions

### Input Validation

**User Input**:
- [ ] All input validated before processing
- [ ] JSON schema validation for components
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (escaping)
- [ ] Path traversal prevented

**WebSocket Input**:
- [ ] All messages validated
- [ ] Entity ownership checked
- [ ] Permissions enforced
- [ ] Rate limiting considered

### Permission Model

**DM vs Player**:
- [ ] Players can only modify their entities
- [ ] DMs have full access
- [ ] Permissions checked on server
- [ ] Client UI reflects permissions

**World Isolation**:
- [ ] Users can only access their worlds
- [ ] No cross-world data leakage
- [ ] File paths validated

### Data Integrity

**Foreign Keys**:
- [ ] Entity deletions cascade appropriately
- [ ] Orphaned components prevented
- [ ] Orphaned relationships prevented

**Soft Delete Consistency**:
- [ ] Deleted entities excluded from queries
- [ ] Relationships to deleted entities handled
- [ ] Components of deleted entities handled

**Schema Validation**:
- [ ] Invalid component data rejected
- [ ] Type mismatches caught
- [ ] Required fields enforced

---

## Execution Strategy

### Per-Phase Process

1. **Create Phase Branch**
   ```bash
   git checkout -b review/phase-N-description
   ```

2. **Systematic Review**
   - Go through each file in scope
   - Use checklist for each item
   - Document findings in FINDINGS.md
   - Mark violations with TODO comments

3. **Categorize Findings**
   - **Critical**: Violates core philosophy, must fix
   - **Important**: Should fix, but not breaking
   - **Minor**: Nice to have improvements
   - **Question**: Need clarification

4. **Plan Fixes**
   - Assess ripple effects
   - Plan mitigation strategy
   - Estimate effort
   - Determine dependencies

5. **Implement Fixes**
   - Start with isolated fixes
   - Then dependent issues in order
   - Write tests for each fix
   - Update documentation

6. **Validate Phase**
   - Run full test suite
   - Manual testing
   - Review against philosophy
   - Update documentation

7. **Commit and Continue**
   ```bash
   git commit -m "Phase N: [description] - [summary]"
   git checkout main
   git merge review/phase-N-description
   ```

### Recommended Order

Execute phases in this order to minimize rework:

1. Phase 1 (Core) - Foundation first
2. Phase 5 (Events) - Event system used by everything
3. Phase 2 (Modules) - Business logic
4. Phase 3 (Components) - Data modeling
5. Phase 4 (Relationships) - Graph structure
6. Phase 6 (Frontend) - User-facing layer
7. Phase 7 (Cross-cutting) - Patterns across layers
8. Phase 8 (Testing/Docs) - Verification
9. Phase 9 (Performance) - Optimize after correctness
10. Phase 10 (Security) - Final hardening

### Success Criteria

✅ All phases completed
✅ All critical violations fixed
✅ Documentation updated and consistent
✅ Test suite passes 100%
✅ No anti-patterns in codebase
✅ Philosophy principles followed throughout
✅ Ripple effects documented
✅ Migration paths provided for breaking changes

---

## Quick Reference: Common Searches

```bash
# Find all StateEngine usages
grep -r "StateEngine" src/

# Find all event emissions
grep -r "event_bus.emit" src/
grep -r "socketio.emit" src/

# Find all event subscriptions
grep -r "event_bus.subscribe" src/
grep -r "socket.on" src/web/

# Find all component type usages
grep -r "add_component.*ComponentName" src/

# Find all relationship creations
grep -r "create_relationship" src/

# Find HTMX attributes in templates
grep -r "hx-get\|hx-post" src/web/templates/

# Find Alpine data bindings
grep -r "x-data\|x-init" src/web/templates/

# Find all Result object returns
grep -r "Result\.ok\|Result\.fail" src/

# Find potential XSS vulnerabilities (missing escaping)
grep -r "{{ [^|]*}}" src/web/templates/  # Look for {{ var }} without | e
```

---

**End of Philosophy Distillation & Review Plan**
