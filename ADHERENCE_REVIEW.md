# Codebase Adherence Review - 2025-11-08

Review of Arcane Arsenal codebase against new implementation guides.

---

## Guides Reviewed Against

1. **IMPLEMENTATION_GUIDE.md** - Backend architectural principles
2. **FRONTEND_IMPLEMENTATION_GUIDE.md** - Frontend architectural principles
3. **MODULE_GUIDE.md** - Module development principles

---

## Findings

### ✅ Compliant Areas

**Backend (IMPLEMENTATION_GUIDE.md):**
- ✅ Composition over inheritance - No entity subclasses found
- ✅ Event-driven architecture - All state changes emit events
- ✅ Validation in code - JSON schemas validate component data
- ✅ Explicit types - All component/relationship/event types registered
- ✅ Soft deletes - Entities/components use deleted_at timestamps
- ✅ No entity IDs in components - Relationships used for connections
- ✅ Component granularity - Components follow single responsibility
- ✅ Result objects - Error handling uses Result.ok()/Result.fail()

**Frontend (FRONTEND_IMPLEMENTATION_GUIDE.md):**
- ✅ Progressive enhancement - HTML works without JS, enhanced with HTMX/Alpine
- ✅ State management - Game state in database, UI state in Alpine
- ✅ Technology boundaries - HTMX for requests, Alpine for reactivity, WebSocket for real-time
- ✅ Scoped Alpine data - Components have isolated x-data scopes
- ✅ No client game state - Inventory, HP, etc. stored in database
- ✅ x-cloak usage - Prevents flash of unstyled content

**Modules (MODULE_GUIDE.md):**
- ✅ Module structure - Proper directory layout (components/, systems/)
- ✅ Component design - Schema-first with clear validation
- ✅ No tight coupling - Modules use events for communication
- ✅ Self-contained - Modules don't modify core code
- ⚠️ UI integration - PARTIAL (see violations section)
- ✅ Event handling - Modules subscribe to relevant events

---

## Active Violations

### ❌ RNG Module UI Hardcoded in Core Templates

**Issue:** RNG module UI is hardcoded in core templates instead of being provided by the module

**MODULE_GUIDE.md states:**
> "Provide UI
> - Component renderers for character sheets
> - Web components for complex interactions
> - Styles scoped to module components"

**Census of Module UI Implementation:**

| Module | Components | Has Renderers? | UI Location | Compliant? |
|--------|-----------|----------------|-------------|------------|
| **generic_fantasy** | Attributes | ✅ YES | `attributes.py::get_character_sheet_renderer()` | ✅ COMPLIANT |
| **fantasy_combat** | Health, Armor | ✅ YES | `__init__.py::get_character_sheet_renderer()` | ✅ COMPLIANT |
| **core_components** | Identity, Position | ❌ NO | Generic form builder fallback | ⚠️ ACCEPTABLE (core module) |
| **items** | (inventory components) | ❌ NO | Generic form builder fallback | ⚠️ ACCEPTABLE (no special UI needs) |
| **rng** | Luck, RollModifier | ❌ NO | **Hardcoded in core templates** | ❌ VIOLATION |

**Violation Details:**

**Location:** `src/web/templates/client/character_sheet.html`
- Lines 76-103: Roll History UI (hardcoded, conditionally rendered via `{% if rng_enabled %}`)
- Lines 106-136: Dice roll toast UI (hardcoded, conditionally rendered via `{% if rng_enabled %}`)

**Evidence:**
```python
# src/modules/rng/__init__.py
# NO get_character_sheet_renderer() method exists
# NO web/ or templates/ directory in module

# src/web/templates/client/character_sheet.html (lines 76-77)
{% if rng_enabled %}
<div class="component-card roll-history-card non-collapsible">
    <!-- Roll History UI hardcoded here -->
```

**Impact:**
- RNG module UI cannot be modified without editing core templates
- Violates module self-containment principle
- Core template has knowledge of module-specific features
- Breaks abstraction: template checks `rng_enabled` flag instead of asking module for UI

**Why This Matters:**
- Other modules (generic_fantasy, fantasy_combat) correctly provide their own renderers
- RNG is a **non-core** module (can be enabled/disabled) but has UI in core templates
- Sets bad precedent for future modules

**Recommended Fix:**
1. Create `src/modules/rng/components.py::get_character_sheet_renderer()` for Roll History
2. OR: Create web component `<rng-roll-history>` in `src/web/static/modules/rng/`
3. Remove hardcoded UI from character_sheet.html
4. Use conditional component rendering pattern instead of template conditionals

**Priority:** Medium - Architectural debt, not functional bug

---

## Violations Fixed

### ❌ Event Naming Violation

**Issue:** `roll.requested` event type violates past-tense naming convention

**IMPLEMENTATION_GUIDE.md states:**
> "Events are Not Commands
> - Event: "character.health_changed" (past tense, fact)
> - Not: "change_character_health" (imperative, command)"

**Violation:**
- Event type `roll.requested` is command-style (imperative)
- Should be past-tense to indicate a fact that happened

**Fix Applied:**
- Renamed `roll.requested` → `roll.initiated`
- Updated function name: `roll_requested_event()` → `roll_initiated_event()`
- Updated handler: `on_roll_requested()` → `on_roll_initiated()`
- Updated all references in:
  - `src/modules/rng/events.py`
  - `src/modules/rng/__init__.py`
  - `src/web/server.py`
  - `tests/test_rng_module.py`
  - `src/modules/rng/README.md`

**Rationale:**
- "roll.initiated" indicates a roll process has started (past tense, fact)
- More accurate semantically - event emitted AFTER roll is initiated
- Aligns with other event names: entity.created, component.added, etc.
- Maintains event-as-history philosophy

---

## Acceptable Deviations

### Module Storage Access

**Observation:** Some modules access `engine.storage` directly for registry operations

**Examples:**
```python
valid_types = {rt['type'] for rt in engine.storage.get_roll_types()}
registry.register_in_registry(..., self.storage, ...)
```

**Analysis:**
- MODULE_GUIDE.md states: "Modules Don't Access Database Directly"
- However, these are registry operations (metadata), not game state
- No alternative StateEngine API exists for registries
- Registries are module-specific type definitions, not ECS data

**Decision:** ACCEPTABLE
- Registry operations are module metadata, not game state
- No violation of state management principles
- Would require StateEngine API extension to fix (future enhancement)
- Does not compromise architecture or AI-friendliness

**Future Improvement:**
- Add StateEngine methods: `get_registry()`, `register_in_registry()`
- Encapsulate storage access for registries
- Low priority - does not affect current functionality

---

## Summary

**Overall Adherence:** ⚠️ Good (with one architectural violation)

**Violations Found:** 2 (event naming, UI integration)
**Violations Fixed:** 1 (event naming)
**Active Violations:** 1 (RNG module UI in core templates)

**Architecture Quality:**
- Core principles strongly adhered to
- ECS pattern properly implemented
- Event-driven design consistent
- Frontend progressive enhancement working well
- Module system mostly clean, with UI integration debt

**Recommendations:**
1. ✅ Continue using past-tense event names
2. ✅ Maintain current component granularity
3. ✅ Keep state in database, not client
4. ⚠️ Consider adding StateEngine registry API (low priority)
5. **⚠️ Refactor RNG module UI out of core templates (medium priority)**

**Priority Actions:**
1. **Medium**: Extract RNG UI from core templates to module
   - Create component renderer or web component
   - Remove `{% if rng_enabled %}` conditionals from character_sheet.html
   - Maintain current functionality while improving architecture

---

**Review Date:** 2025-11-08
**Reviewed By:** Claude (Automated Adherence Review)
**Updated:** 2025-11-08 (UI integration census added)
**Status:** Good overall adherence with architectural debt in RNG module UI integration
