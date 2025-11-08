# Arcane Arsenal - Frontend Implementation Guide

**Purpose**: Strict guidelines for building frontend features in Arcane Arsenal. Focuses on architectural principles, technology choices, and decision-making frameworks with minimal code examples for clarification.

---

## Core Philosophy

### Primary Goals

1. **Progressive Enhancement**: Features work without JavaScript, enhanced with it
2. **Minimal Complexity**: No build step, no framework bloat, no transpilation
3. **Real-time by Default**: WebSocket-first for multiplayer experiences
4. **Module Extensibility**: Modules can add UI without modifying core templates

### Architectural Principles

**Server-Rendered Foundation**
- HTML is generated on the server with full data
- JavaScript enhances, not replaces, server rendering
- Pages work (albeit less smoothly) with JavaScript disabled
- Forms submit via HTTP POST before HTMX adds partial updates

**Separation of Concerns**
- **HTMX**: Server interactions (fetch, submit, update DOM)
- **Alpine.js**: Client state and reactivity (show/hide, counters, toggles)
- **Socket.IO**: Real-time multiplayer events (rolls, HP changes, notifications)
- **Web Components**: Complex, reusable module UI (spell lists, inventory grids)

**State Lives in Database**
- Client state is ephemeral (UI toggles, animations)
- Authoritative state lives in SQLite via StateEngine
- WebSocket events propagate state changes to all clients
- Never trust client for game-critical state (HP, inventory, stats)

---

## Technology Stack

### When to Use What

| Requirement | Solution | Example |
|-------------|----------|---------|
| Fetch data from server | HTMX `hx-get` | Load entity details on click |
| Submit form without reload | HTMX `hx-post` | Update character name |
| Toggle visibility | Alpine `x-show` | Collapsible inventory section |
| Client-side computation | Alpine `x-data` | Calculate HP percentage |
| Real-time multiplayer sync | Socket.IO `emit/on` | Broadcast dice rolls |
| Complex reusable UI | Web Component | Spell list with filtering |

### Technology Boundaries

**HTMX Does:**
- Partial page updates (swap HTML fragments)
- Form submissions without full reload
- Polling for server updates (`hx-trigger="every 5s"`)
- Simple request/response patterns

**HTMX Doesn't:**
- Manage client state (no variables)
- Handle complex reactivity
- Support real-time WebSocket events
- Provide animations or transitions

**Alpine.js Does:**
- Client-side reactive state (`x-data`)
- Show/hide elements (`x-show`, `x-if`)
- Event handling (`@click`, `@submit`)
- Computed properties (getters in `x-data`)
- Transitions (`x-transition`)

**Alpine.js Doesn't:**
- Make HTTP requests (use HTMX or fetch)
- Persist state (state resets on page reload)
- Communicate with WebSockets directly (use global socket)
- Replace server rendering

**Socket.IO Does:**
- Bi-directional real-time communication
- Broadcast events to multiple clients
- Room-based messaging (world rooms, entity rooms)
- Automatic reconnection

**Socket.IO Doesn't:**
- Replace REST APIs for simple CRUD
- Store state (it's a transport layer)
- Guarantee message ordering (handle edge cases)

---

## State Management

### State Hierarchy

**Database State (Source of Truth)**
- Entity data, components, relationships
- Modified via StateEngine API
- Persisted across sessions
- Example: Character HP, inventory contents, position

**Server Session State**
- User authentication, selected world, active character
- Lives in Flask session
- Resets on logout
- Example: Current world name, user ID

**Client Ephemeral State (Alpine.js)**
- UI toggles, animations, form inputs
- Resets on page reload
- Not synced between clients
- Example: Inventory panel open/closed, roll history visibility

**Client Derived State**
- Computed from database or session state
- Calculated in Alpine getters or templates
- Example: HP percentage, modifier from ability score

### State Synchronization

**Server → Client (Initial Load)**
1. Flask renders template with Jinja2
2. Template includes entity data in HTML
3. Alpine initializes with server-provided values: `x-data="{ hp: {{ current_hp }} }"`

**Client → Server (Mutations)**
1. User interacts (clicks button, submits form)
2. HTMX posts to API endpoint OR Socket.IO emits event
3. Server validates and mutates database
4. Server broadcasts event via WebSocket to all clients

**Server → Clients (Real-time Updates)**
1. Server emits WebSocket event (e.g., `hp_updated`)
2. All connected clients in room receive event
3. Alpine reactive state updates: `socket.on('hp_updated', (d) => this.hp = d.current_hp)`
4. UI re-renders automatically via Alpine reactivity

### Avoiding State Drift

**Don't Duplicate State**
- ❌ Storing HP in Alpine AND database, updating only one
- ✅ Store HP in database, Alpine holds a reactive copy updated via WebSocket

**Don't Trust Client Math**
- ❌ Client calculates `newHP = currentHP - damage`, sends `newHP`
- ✅ Client sends `damage` amount, server calculates and validates

**Don't Mutate Without Sync**
- ❌ Alpine decrements HP locally, eventually syncs to server
- ✅ Alpine emits event, waits for server confirmation, updates on `hp_updated` event

---

## Component Patterns

### Progressive Enhancement Layers

**Layer 1: HTML-Only (Base)**
```html
<form method="POST" action="/api/entity/123/heal">
    <input name="amount" value="10">
    <button type="submit">Heal</button>
</form>
```
- Works without JavaScript
- Full page reload on submit
- Accessible, SEO-friendly

**Layer 2: HTMX (Partial Updates)**
```html
<form hx-post="/api/entity/123/heal" hx-target="#hp-display" hx-swap="innerHTML">
    <input name="amount" value="10">
    <button type="submit">Heal</button>
</form>
```
- No page reload, swaps `#hp-display` content
- Graceful degradation if HTMX fails to load

**Layer 3: Alpine (Client State)**
```html
<form hx-post="/api/entity/123/heal" hx-target="#hp-display"
      x-data="{ amount: 10 }">
    <input x-model="amount">
    <button type="submit">Heal <span x-text="amount"></span></button>
</form>
```
- Live preview of heal amount as user types
- Still functions if Alpine fails

**Layer 4: WebSocket (Real-time)**
```html
<div x-data="{ hp: {{ current_hp }} }"
     x-init="socket.on('hp_updated', (d) => hp = d.current_hp)">
    HP: <span x-text="hp"></span>
</div>
```
- Updates across all clients in real-time
- Falls back to polling or manual refresh if WebSocket disconnects

### Scoping Patterns

**Scope Alpine Data to Components**
- Each collapsible section, card, or widget gets its own `x-data`
- Avoid page-level global state
- Prevents naming conflicts and improves performance

**Good Scoping:**
```html
<div class="inventory-card" x-data="{ open: false }">
    <h3 @click="open = !open">Inventory</h3>
    <div x-show="open">Items...</div>
</div>

<div class="spells-card" x-data="{ open: false }">
    <h3 @click="open = !open">Spells</h3>
    <div x-show="open">Spells...</div>
</div>
```

**Bad Scoping:**
```html
<div x-data="{ inventoryOpen: false, spellsOpen: false, healthOpen: false }">
    <!-- Entire page here -->
</div>
```

### Reusable Alpine Components

**When to Create an Alpine Component**
- Logic is used in multiple places (dice roller, health tracker)
- State and behavior are tightly coupled
- Component has clear inputs/outputs

**How to Define:**
```javascript
Alpine.data('componentName', (param1, param2) => ({
    // State
    localState: param1,

    // Computed properties
    get derivedValue() {
        return this.localState * 2;
    },

    // Methods
    doSomething() {
        this.localState++;
    },

    // Lifecycle
    init() {
        // Setup event listeners, subscriptions
    }
}));
```

**Usage:**
```html
<div x-data="componentName(initialValue, config)">
    <span x-text="derivedValue"></span>
    <button @click="doSomething()">Click</button>
</div>
```

### Web Component Patterns

**When to Use Web Components**
- Complex UI that modules provide (spell lists, skill trees, map viewers)
- Encapsulated behavior (internal DOM, shadow DOM, styles)
- Reusable across different contexts (character sheet, DM view, mobile)

**When NOT to Use Web Components**
- Simple toggles or forms (use Alpine)
- One-off UI elements (inline HTML)
- Performance-critical updates (Alpine is faster for simple reactivity)

**Web Component Structure:**
```javascript
class MyComponent extends HTMLElement {
    connectedCallback() {
        // Parse attributes
        this.entityId = this.getAttribute('entity-id');

        // Initial render
        this.render();

        // Setup event listeners
        this.setupListeners();
    }

    disconnectedCallback() {
        // Cleanup subscriptions
    }

    render() {
        // Generate HTML (can use Alpine inside)
        this.innerHTML = `<div x-data="...">...</div>`;
    }
}
customElements.define('my-component', MyComponent);
```

---

## Real-time Communication

### WebSocket Event Patterns

**Room-Based Broadcasting**
- World room: All players in a campaign (`world_my_campaign`)
- Entity room: All views of a specific entity (`entity_char_123`)
- Join rooms on page load, leave on disconnect

**Event Naming Convention**
- Past tense, describes what happened
- Scoped by domain: `roll_result`, `hp_updated`, `spell_cast`
- Generic events: `game_event` with `event_type` field

**Event Flow:**
1. Client emits event: `socket.emit('roll_dice', {...})`
2. Server validates and processes
3. Server emits to room: `socketio.emit('roll_result', {...}, room='world_x')`
4. All clients in room receive and react

### Client Event Handling

**Subscribe in Alpine init:**
```javascript
Alpine.data('diceRoller', () => ({
    result: null,

    init() {
        socket.on('roll_result', (data) => {
            this.result = data;
        });
    },

    roll(notation) {
        socket.emit('roll_dice', { notation });
    }
}));
```

**Subscribe in Web Component:**
```javascript
connectedCallback() {
    this.handleRoll = (data) => this.updateDisplay(data);
    socket.on('roll_result', this.handleRoll);
}

disconnectedCallback() {
    socket.off('roll_result', this.handleRoll);
}
```

### Error Handling

**Reconnection:**
- Socket.IO handles automatic reconnection
- Show reconnection UI if needed: `socket.on('disconnect', ...)`
- Re-join rooms on reconnect: `socket.on('connect', ...)`

**Message Validation:**
- Server validates all incoming messages
- Client should handle malformed events gracefully
- Use optional chaining: `data?.total` instead of `data.total`

**Idempotency:**
- Handle duplicate events (network retries)
- Use event IDs to deduplicate if necessary
- Don't assume events arrive in order

---

## Data Flow

### Server to Client

**Template Rendering (Jinja2):**
- Use for initial page load
- Pass data as HTML or as Alpine initial state
- Escape all user data: `{{ name | e }}`

**HTMX Responses:**
- Return HTML fragments, not JSON
- Server renders updated section
- HTMX swaps into target element

**WebSocket Events:**
- Send structured JSON payloads
- Include all necessary context (entity ID, new values, metadata)
- Don't send HTML over WebSocket (not cacheable, harder to version)

### Client to Server

**HTMX Requests:**
- Form data or query params
- Server processes and returns HTML
- Validation errors rendered as HTML

**WebSocket Events:**
- Send minimal payloads (entity ID, action, parameters)
- Server fetches entity state from database
- Server validates all inputs before mutation

**API Design:**
- HTMX endpoints return HTML fragments
- WebSocket handlers emit events, don't return values
- Use Result objects for error handling on server

---

## Visibility and Transitions

### Conditional Rendering

**x-show vs x-if:**
- `x-show`: Element stays in DOM, visibility toggled (fast, keeps state)
- `x-if`: Element removed from DOM entirely (slower, resets state)

**When to use x-show:**
- Frequently toggled (inventory open/close)
- Contains form inputs that should persist
- Simple visibility toggle

**When to use x-if:**
- Rarely shown, expensive to render
- Should reset state when hidden
- Conditional on data presence

**Example:**
```html
<!-- Toggle visibility: use x-show -->
<div x-show="open" x-transition>...</div>

<!-- Conditional rendering: use x-if -->
<template x-if="items.length === 0">
    <p>No items found</p>
</template>
```

### Transitions

**Use x-transition for:**
- Smooth show/hide (fade, slide)
- Non-critical UI polish
- Improving perceived performance

**Don't use for:**
- Critical UI (loading states, errors)
- Performance-sensitive updates (many items)

**Modifiers:**
- `x-transition` (default fade)
- `x-transition.opacity` (opacity only)
- `x-transition.scale.90` (scale from 90%)
- `x-transition.duration.500ms` (custom duration)

---

## Module Integration

### Module Responsibilities

**Modules Provide:**
- Custom component renderers (return HTML strings)
- Web resources (JS files, CSS files)
- Web component definitions (custom elements)
- Alpine component definitions (via registration)

**Modules Don't:**
- Modify core templates (extend, not replace)
- Access Flask routes directly (use APIs)
- Store UI state (use database or Alpine)

### Component Rendering

**Server-Side Rendering:**
```python
class InventoryComponent(ComponentTypeDefinition):
    def get_character_sheet_renderer(self, data, engine=None):
        items = data.get('items', [])
        return f'''
        <div class="inventory" x-data="collapsible(false)">
            <h3 @click="toggle()">Inventory ({len(items)} items)</h3>
            <div x-show="open" x-transition>
                <!-- Items list -->
            </div>
        </div>
        '''
```

**Key Points:**
- Return HTML string with Alpine/HTMX attributes
- Use `engine` parameter for context (entity ID, world name)
- Escape user data with `markupsafe.escape()`
- Can embed Web Components in returned HTML

### Resource Loading

**Static Files:**
- Module JS/CSS goes in `src/web/static/modules/my_module/`
- Register in module's `register_web_resources()`
- Core loads resources automatically

**Web Components:**
- Define in separate JS files
- Use `customElements.define('component-name', ComponentClass)`
- Can use Alpine inside component's innerHTML

---

## Common Patterns

### Collapsible Sections

**Using Built-in Alpine Component:**
```html
<div x-data="collapsible(false)">
    <h3 @click="toggle()">
        <span x-text="open ? '▼' : '▶'"></span> Section Title
    </h3>
    <div x-show="open" x-transition>Content</div>
</div>
```

**Custom Logic:**
```html
<div x-data="{ open: false }">
    <h3 @click="open = !open" :data-collapsed="!open">Title</h3>
    <div x-show="open">Content</div>
</div>
```

### Form Validation

**Client-Side (Alpine):**
```html
<div x-data="{ hp: 50, max: 100, get valid() { return this.hp >= 0 && this.hp <= this.max; } }">
    <input x-model="hp" type="number">
    <button :disabled="!valid">Update HP</button>
    <p x-show="!valid" class="error">HP must be between 0 and 100</p>
</div>
```

**Server-Side (Always Required):**
- Validate in Flask route or WebSocket handler
- Return error HTML or emit error event
- Never trust client validation alone

### Polling for Updates

**Use HTMX polling sparingly:**
```html
<div hx-get="/api/entity/123/hp"
     hx-trigger="every 5s"
     hx-swap="innerHTML">
</div>
```

**Prefer WebSocket for real-time:**
```html
<div x-data="{ hp: {{ current_hp }} }"
     x-init="socket.on('hp_updated', (d) => hp = d.current_hp)">
</div>
```

### Loading States

**HTMX Indicators:**
```html
<div hx-get="/api/data" hx-indicator="#spinner">
    Content
</div>
<div id="spinner" class="htmx-indicator">Loading...</div>
```

**Alpine Indicators:**
```html
<div x-data="{ loading: false }">
    <button @click="loading = true; fetch(...).finally(() => loading = false)">
        <span x-show="!loading">Load</span>
        <span x-show="loading">Loading...</span>
    </button>
</div>
```

---

## Anti-Patterns

### ❌ Don't Mix Concerns

**Bad: HTMX and Alpine fighting for control**
```html
<div x-data="{ hp: 50 }">
    <div hx-get="/api/hp" hx-trigger="load" hx-swap="innerHTML">
        <span x-text="hp"></span>
    </div>
</div>
```
HTMX will replace the Alpine-bound element, breaking reactivity.

**Good: Choose one approach**
```html
<!-- Option 1: HTMX only -->
<div hx-get="/api/hp" hx-trigger="load">Loading...</div>

<!-- Option 2: Alpine + WebSocket -->
<div x-data="{ hp: 50 }" x-init="socket.on('hp_updated', (d) => hp = d.current_hp)">
    <span x-text="hp"></span>
</div>
```

### ❌ Don't Store Game State in Alpine

**Bad: Client as source of truth**
```html
<div x-data="{ inventory: [] }">
    <button @click="inventory.push({ name: 'Sword' })">Add Sword</button>
</div>
```
Resets on page reload, not synced to server, not multiplayer-safe.

**Good: Server as source of truth**
```html
<div x-data="{ inventory: {{ inventory_json }} }">
    <button hx-post="/api/inventory/add" hx-vals='{"item": "Sword"}'>Add Sword</button>
</div>
```

### ❌ Don't Use WebSocket for Simple Requests

**Bad: Overcomplicated**
```javascript
socket.emit('get_hp', { entity_id: '123' });
socket.on('hp_response', (data) => { ... });
```

**Good: Use HTMX**
```html
<button hx-get="/api/entity/123/hp" hx-target="#hp-display">Get HP</button>
```

### ❌ Don't Ignore Accessibility

**Bad: No keyboard access**
```html
<div @click="open = !open">Toggle</div>
```

**Good: Use semantic elements**
```html
<button @click="open = !open">Toggle</button>
```

### ❌ Don't Hardcode Entity IDs

**Bad: Magic strings**
```javascript
socket.emit('roll_dice', { entity_id: 'char_123' });
```

**Good: Use template variables**
```javascript
socket.emit('roll_dice', { entity_id: '{{ entity.id }}' });
```

### ❌ Don't Forget to Escape User Data

**Bad: XSS vulnerability**
```python
return f'<div>{data["name"]}</div>'
```

**Good: Escape all user input**
```python
from markupsafe import escape
return f'<div>{escape(data["name"])}</div>'
```

---

## Testing & Debugging

### Browser DevTools

**Console Checks:**
- `Alpine` - Should be defined if Alpine loaded
- `socket.connected` - Should be `true` if connected
- `htmx` - Should be defined if HTMX loaded

**Network Tab:**
- HTMX requests appear as XHR/Fetch
- Check `hx-request` header to identify HTMX calls
- WebSocket appears as `ws://` connection

**Alpine DevTools:**
- Install Alpine.js DevTools browser extension
- Inspect component state live
- Track reactivity updates

### Common Issues

**Alpine not updating:**
- Check for typos in `x-text`, `x-show`, etc.
- Ensure data is reactive (defined in `x-data`)
- Look for JavaScript errors in console

**HTMX not swapping:**
- Verify target element exists (`hx-target`)
- Check server response is HTML, not JSON
- Ensure swap strategy is appropriate

**WebSocket not receiving:**
- Check room membership (`join_world`, `join_entity`)
- Verify event name matches server emit
- Look for connection errors in console

---

## Design Decision Framework

### When Adding a UI Feature

**1. Identify the Interaction Pattern**
- Is this a one-time request? → HTMX
- Is this local UI state? → Alpine
- Is this real-time multiplayer? → WebSocket
- Is this complex/reusable? → Web Component

**2. Determine State Location**
- Does this need to persist? → Database
- Is this session-specific? → Flask session
- Is this UI-only? → Alpine

**3. Choose Enhancement Level**
- Start with HTML form/link
- Add HTMX for partial updates
- Add Alpine for client reactivity
- Add WebSocket for real-time

**4. Plan Error Handling**
- What happens if JavaScript fails?
- What happens if WebSocket disconnects?
- How do we show errors to user?

**5. Consider Accessibility**
- Can this be keyboard-navigated?
- Does this have proper ARIA labels?
- Is focus management correct?

---

## Consistency Checklist

Before merging frontend features:

- [ ] Progressive enhancement: works without JS
- [ ] User data is escaped in all renderers
- [ ] Alpine state is scoped to components
- [ ] WebSocket used only for real-time features
- [ ] HTMX used for server interactions
- [ ] Loading/error states are handled
- [ ] Keyboard accessibility verified
- [ ] No client-side game state storage
- [ ] Events have clear, past-tense names
- [ ] Web components clean up on disconnect
- [ ] No hardcoded entity IDs or magic strings
- [ ] Transitions enhance, don't block UX

---

## Summary

**Arcane Arsenal frontend is:**
- Progressively enhanced (HTML → HTMX → Alpine → WebSocket)
- Lightweight and build-free
- Real-time by default via WebSocket
- Modular and extensible

**When building UI:**
- Start with server-rendered HTML
- Add HTMX for partial updates
- Add Alpine for client reactivity
- Add WebSocket for multiplayer sync
- Use Web Components for complex modules

**Always ask:**
- Does this work without JavaScript?
- Is state in the right place?
- Am I using the right tool (HTMX/Alpine/Socket)?
- Is this accessible?
- Will this scale to multiplayer?

**Technology Decision Tree:**
```
Need to...
├─ Fetch/submit data once?
│  └─ Use HTMX (hx-get, hx-post)
├─ Toggle/animate UI?
│  └─ Use Alpine (x-show, x-transition)
├─ Sync state real-time?
│  └─ Use WebSocket (emit/on)
├─ Build complex reusable UI?
│  └─ Use Web Component (customElements.define)
└─ Just display data?
   └─ Use plain HTML (Jinja2 template)
```

---

**Last Updated**: 2025-11-08
