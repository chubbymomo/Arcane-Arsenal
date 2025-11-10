# Frontend System Guide

Complete guide to the Arcane Arsenal frontend architecture for module developers.

## Overview

Arcane Arsenal uses a modern, lightweight frontend stack designed for **extensibility**:

- **HTMX** (1.9.10) - Hypermedia-driven interactions
- **Alpine.js** (3.13.3) - Reactive client state
- **Socket.IO** (4.5.4) - Real-time WebSocket communication
- **Web Components** - Module-specific custom elements

**Total Size**: ~50KB (including Socket.IO)
**Build Step**: None required
**Module Barrier**: Low - HTML knowledge sufficient for basic modules

---

## Architecture Layers

### 1. Server-Side (Python)

Modules define rendering logic in component definitions:

```python
class HealthComponent(ComponentTypeDefinition):
    def get_character_sheet_renderer(self, data, engine=None):
        """Custom HTML with HTMX/Alpine attributes."""
        return f'''
        <div x-data="healthTracker({data['current_hp']}, {data['max_hp']})">
            <div class="health-bar">
                HP: <span x-text="current"></span>/<span x-text="max"></span>
            </div>
            <button @click="damage(5)">Take 5 Damage</button>
            <button hx-post="/api/heal/{entity_id}" hx-vals='{"amount": 10}'>
                Heal 10 HP
            </button>
        </div>
        '''
```

### 2. HTMX Layer

For server interactions without JavaScript:

```html
<!-- Load entity data without page reload -->
<div hx-get="/api/entity/{{entity_id}}/health"
     hx-trigger="load, every 5s"
     hx-swap="innerHTML">
</div>

<!-- Submit form with partial update -->
<form hx-post="/api/entity/{{entity_id}}/update"
      hx-target="#status"
      hx-swap="outerHTML">
</form>

<!-- Roll dice via server -->
<button hx-post="/api/roll/1d20+5"
        hx-target="#roll-result"
        hx-swap="innerHTML">
    Roll Attack
</button>
```

### 3. Alpine.js Layer

For client-side state and interactivity:

```html
<!-- Collapsible inventory -->
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle Inventory</button>
    <div x-show="open" x-transition>
        <!-- Items list -->
    </div>
</div>

<!-- Dice roller with animation -->
<div x-data="diceRoller()">
    <button @click="roll('1d20+5', '{{entity_id}}', 'attack')">
        Roll Attack
    </button>
    <div x-show="rolling" class="spinner"></div>
    <div x-show="result" x-text="result?.breakdown" x-transition></div>
</div>

<!-- HP tracker with computed values -->
<div x-data="{ current: 45, max: 60 }">
    <div>HP: <span x-text="current"></span>/<span x-text="max"></span></div>
    <div>Percentage: <span x-text="Math.round(current / max * 100)"></span>%</div>
</div>
```

### 4. WebSocket Layer

For real-time multiplayer features:

```javascript
// Client-side (automatically available in templates)
socket.emit('roll_dice', {
    entity_id: 'character_123',
    notation: '1d20+5',
    roll_type: 'attack',
    purpose: 'Attack goblin'
});

socket.on('roll_result', (data) => {
    console.log('Roll:', data.total, data.breakdown);
});

socket.on('hp_updated', (data) => {
    console.log(`${data.entity_id} HP: ${data.current_hp}/${data.max_hp}`);
});
```

### 5. Web Components Layer

For complex, encapsulated module UI:

```javascript
// src/modules/spells/web/spell-list.js
class SpellList extends HTMLElement {
    connectedCallback() {
        this.entityId = this.getAttribute('entity-id');
        this.loadSpells();
    }

    async loadSpells() {
        const response = await fetch(`/api/entity/${this.entityId}/spells`);
        const spells = await response.json();
        this.render(spells);
    }

    render(spells) {
        this.innerHTML = `
            <div class="spell-list" x-data="{ selected: null }">
                ${spells.map(spell => `
                    <div class="spell-card"
                         @click="selected = '${spell.id}'"
                         :class="{ 'selected': selected === '${spell.id}' }">
                        <h3>${spell.name}</h3>
                        <p>${spell.description}</p>
                        <button hx-post="/api/cast/${spell.id}"
                                hx-target="#spell-result">
                            Cast Spell
                        </button>
                    </div>
                `).join('')}
            </div>
        `;
    }
}
customElements.define('spell-list', SpellList);
```

---

## Module Integration

### Step 1: Define Web Resources

```python
# src/modules/my_module/__init__.py
class MyModule(Module):
    def register_web_resources(self):
        return {
            'scripts': [
                '/static/modules/my_module/my-component.js',
                '/static/modules/my_module/utils.js'
            ],
            'styles': [
                '/static/modules/my_module/styles.css'
            ],
            'components': ['my-component', 'my-widget']
        }
```

### Step 2: Create Web Component

```javascript
// src/modules/my_module/web/my-component.js
class MyComponent extends HTMLElement {
    connectedCallback() {
        const entityId = this.getAttribute('entity-id');
        const config = JSON.parse(this.getAttribute('config') || '{}');

        this.render();
        this.setupEventListeners();
    }

    render() {
        this.innerHTML = `
            <div class="my-component"
                 x-data="{ count: 0 }"
                 hx-get="/api/my-data"
                 hx-trigger="load">
                <button @click="count++">Clicked <span x-text="count"></span> times</button>
            </div>
        `;
    }

    setupEventListeners() {
        // Listen for WebSocket events
        socket.on('my_event', (data) => {
            console.log('Received:', data);
            this.update(data);
        });
    }

    update(data) {
        // Update component with new data
    }
}
customElements.define('my-component', MyComponent);
```

### Step 3: Use in Component Renderer

```python
class MyCustomComponent(ComponentTypeDefinition):
    def get_character_sheet_renderer(self, data, engine=None):
        return f'''
        <my-component
            entity-id="{engine.current_entity_id if engine else ''}"
            config='{json.dumps(data)}'>
        </my-component>
        '''
```

---

## Built-in Alpine.js Components

Arcane Arsenal provides these ready-to-use Alpine components:

### diceRoller()

```html
<div x-data="diceRoller()">
    <button @click="roll('1d20+5', entityId, 'attack', 'Attack goblin')">
        Roll Attack
    </button>
    <div x-show="rolling">Rolling...</div>
    <div x-show="result">
        Result: <span x-text="result?.total"></span>
        <span x-text="result?.breakdown"></span>
    </div>

    <!-- Roll history -->
    <template x-for="roll in history">
        <div x-text="roll.breakdown"></div>
    </template>
</div>
```

### healthTracker(current, max)

```html
<div x-data="healthTracker(45, 60)">
    <div>HP: <span x-text="current"></span>/<span x-text="max"></span></div>
    <div>
        <span x-text="percentage"></span>%
        (<span x-text="color"></span>)
    </div>

    <button @click="damage(5)">-5 HP</button>
    <button @click="heal(10)">+10 HP</button>
</div>
```

### collapsible(startOpen)

```html
<div x-data="collapsible(false)">
    <button @click="toggle()">
        <span x-text="open ? '▼' : '▶'"></span> Inventory
    </button>
    <div x-show="open" x-transition>
        <!-- Collapsible content -->
    </div>
</div>
```

### DM-Only: eventMonitor()

```html
<div x-data="eventMonitor()">
    <h3>Live Game Events</h3>
    <template x-for="event in events">
        <div x-text="`${event.event_type}: ${event.message}`"></div>
    </template>
</div>
```

---

## WebSocket Events

### Client → Server

**roll_dice**
```javascript
socket.emit('roll_dice', {
    entity_id: 'char_123',
    notation: '1d20+5',
    roll_type: 'attack',
    purpose: 'Attack goblin'
});
```

**update_hp**
```javascript
socket.emit('update_hp', {
    entity_id: 'char_123',
    current_hp: 45,
    max_hp: 60,
    temp_hp: 5
});
```

**broadcast_event** (DM only)
```javascript
socket.emit('broadcast_event', {
    event_type: 'notification',
    message: 'A dragon appears!',
    data: { dragon_id: 'dragon_001' }
});
```

**join_world**
```javascript
socket.emit('join_world', { world_name: 'my_campaign' });
```

**join_entity**
```javascript
socket.emit('join_entity', { entity_id: 'char_123' });
```

### Server → Client

**roll_result**
```javascript
socket.on('roll_result', (data) => {
    // data.total, data.breakdown, data.critical, etc.
});
```

**hp_updated**
```javascript
socket.on('hp_updated', (data) => {
    // data.entity_id, data.current_hp, data.max_hp, data.temp_hp
});
```

**game_event**
```javascript
socket.on('game_event', (event) => {
    // event.event_type, event.message, event.data, event.timestamp
});
```

---

## Best Practices

### 1. Progressive Enhancement

Start with server-rendered HTML, add HTMX for partial updates, then Alpine for interactivity:

```html
<!-- Level 1: Server-rendered (works without JS) -->
<form method="POST" action="/api/entity/{{entity_id}}/update">
    <input name="hp" value="{{hp}}">
    <button>Update</button>
</form>

<!-- Level 2: Add HTMX (partial updates) -->
<form hx-post="/api/entity/{{entity_id}}/update" hx-swap="outerHTML">
    <input name="hp" value="{{hp}}">
    <button>Update</button>
</form>

<!-- Level 3: Add Alpine (client state) -->
<form hx-post="/api/entity/{{entity_id}}/update"
      hx-swap="outerHTML"
      x-data="{ hp: {{hp}} }">
    <input x-model="hp">
    <button>Update (<span x-text="hp"></span>)</button>
</form>
```

### 2. Use WebSockets for Real-Time Only

Don't use WebSockets for one-off requests - use HTMX:

```html
<!-- ❌ Bad: WebSocket for simple request -->
<button onclick="socket.emit('get_hp', {entity_id: '123'})">Get HP</button>

<!-- ✅ Good: HTMX for simple request -->
<button hx-get="/api/entity/123/hp" hx-target="#hp-display">Get HP</button>

<!-- ✅ Good: WebSocket for live updates -->
<div x-data="{ hp: 0 }" x-init="socket.on('hp_updated', (d) => hp = d.current_hp)">
    HP: <span x-text="hp"></span>
</div>
```

### 3. Scope Alpine Data

Keep Alpine data scoped to components, not globally:

```html
<!-- ❌ Bad: Global state -->
<div x-data="{ inventory: [...] }">
    <!-- Entire page -->
</div>

<!-- ✅ Good: Scoped state -->
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>
    <div x-show="open"><!-- Collapsible content --></div>
</div>
```

### 4. Escape User Data

Always escape user-provided data in custom renderers:

```python
from markupsafe import escape

def get_character_sheet_renderer(self, data, engine=None):
    name = escape(data.get('name', 'Unknown'))
    description = escape(data.get('description', ''))

    return f'''
    <div class="character">
        <h2>{name}</h2>
        <p>{description}</p>
    </div>
    '''
```

---

## Example: Complete Spell System Module

```python
# src/modules/spells/__init__.py
class SpellsModule(Module):
    @property
    def name(self):
        return "spells"

    @property
    def version(self):
        return "1.0.0"

    def register_component_types(self):
        return [SpellbookComponent, SpellSlotComponent]

    def register_web_resources(self):
        return {
            'scripts': ['/static/modules/spells/spell-list.js'],
            'styles': ['/static/modules/spells/spells.css'],
            'components': ['spell-list']
        }

class SpellbookComponent(ComponentTypeDefinition):
    type = "Spellbook"

    def get_character_sheet_renderer(self, data, engine=None):
        spells = data.get('spells', [])

        return f'''
        <div class="spellbook" x-data="collapsible(true)">
            <h3 @click="toggle()">
                <span x-text="open ? '▼' : '▶'"></span> Spellbook
            </h3>
            <div x-show="open" x-transition>
                <spell-list
                    entity-id="{entity_id if engine else ''}"
                    spells='{json.dumps(spells)}'>
                </spell-list>
            </div>
        </div>
        '''
```

```javascript
// src/web/static/modules/spells/spell-list.js
class SpellList extends HTMLElement {
    connectedCallback() {
        this.entityId = this.getAttribute('entity-id');
        this.spells = JSON.parse(this.getAttribute('spells') || '[]');
        this.render();
    }

    render() {
        this.innerHTML = `
            <div class="spell-grid" x-data="{ casting: null }">
                ${this.spells.map(spell => `
                    <div class="spell-card">
                        <h4>${spell.name}</h4>
                        <p>Level ${spell.level} ${spell.school}</p>
                        <button
                            hx-post="/api/cast/${spell.id}"
                            hx-target="#spell-result"
                            @click="casting = '${spell.id}'"
                            :disabled="casting === '${spell.id}'">
                            Cast
                        </button>
                    </div>
                `).join('')}
            </div>
        `;
    }
}
customElements.define('spell-list', SpellList);
```

---

## Testing

### Check Frontend Loading

1. Open browser DevTools
2. Check Console for: `✅ Connected to Arcane Arsenal server`
3. Verify no HTMX errors
4. Verify Alpine.js loaded: `console.log(Alpine)`

### Test WebSocket

```javascript
// In browser console
socket.emit('roll_dice', {
    entity_id: 'test_123',
    notation: '1d20',
    roll_type: 'check'
});

socket.on('roll_result', (data) => console.log(data));
```

### Test Alpine Component

```javascript
// In browser console
Alpine.data('testComponent', () => ({
    message: 'Hello from Alpine!'
}));
```

---

## Deployment

### Production Considerations

1. **CDN URLs**: Consider hosting HTMX/Alpine/Socket.IO locally for production
2. **CORS**: Configure Socket.IO CORS for your domain
3. **Compression**: Enable gzip/brotli for JavaScript/CSS
4. **Caching**: Set appropriate cache headers for static resources
5. **Security**: Validate all WebSocket messages on server

### Environment Configuration

```python
# server.py
socketio = SocketIO(
    app,
    cors_allowed_origins=os.getenv('ALLOWED_ORIGINS', '*').split(','),
    async_mode='eventlet',
    logger=not os.getenv('PRODUCTION'),
    engineio_logger=False
)
```

---

## Further Reading

- [HTMX Documentation](https://htmx.org/docs/)
- [Alpine.js Documentation](https://alpinejs.dev/)
- [Socket.IO Client API](https://socket.io/docs/v4/client-api/)
- [Web Components MDN](https://developer.mozilla.org/en-US/docs/Web/Web_Components)
