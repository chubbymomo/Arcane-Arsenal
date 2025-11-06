# Character Sheet Redesign - Design Document

**Date**: 2025-11-06
**Author**: Claude
**Status**: Design Phase

---

## 🎯 Goals

1. **Flexibility**: Display ANY component that modules can add
2. **Dice Rolling**: Interactive dice buttons for rollable values
3. **Scalability**: Handle 5 components or 50 components gracefully
4. **Usability**: Quick access to common actions and important stats
5. **Beauty**: Modern, professional RPG character sheet appearance

---

## 📋 Current Problems

### What We Have Now:
- Simple 2-column layout
- Components displayed using `FormBuilder.build_display()`
- Static, read-only display
- No dice rolling
- No component organization/prioritization
- Important stats buried in component lists

### What's Missing:
- ❌ No way to roll dice for ability checks, attacks, etc.
- ❌ No "at-a-glance" view of key stats (AC, HP, Initiative)
- ❌ No component categorization (combat vs. info vs. resources)
- ❌ No interactivity (can't track HP, spell slots, etc.)
- ❌ No priority system (Attributes should be more prominent than misc components)
- ❌ No special handling for common component types (weapons, health, etc.)

---

## 🎨 Proposed Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ CHARACTER HEADER                                                │
│ ┌────────────────┐  Quick Stats: ❤️ HP  🛡️ AC  ⚡ Init  🎯 Prof │
│ │ Gandara        │  [🎲 Initiative Roll]                       │
│ │ Level 3 Ranger │                                              │
│ └────────────────┘                                              │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┬──────────────────────────┬──────────────────┐
│ LEFT COLUMN      │ CENTER COLUMN            │ RIGHT COLUMN     │
│ (Stats & Checks) │ (Combat & Actions)       │ (Info & Inv)     │
├──────────────────┼──────────────────────────┼──────────────────┤
│                  │                          │                  │
│ ┏━━━━━━━━━━━┓    │ ⚔️ COMBAT               │ 📜 DETAILS       │
│ ┃ ATTRIBUTES┃    │                          │                  │
│ ┗━━━━━━━━━━━┛    │ ┌─────────────────────┐ │ Race: Elf        │
│                  │ │ Longbow             │ │ Class: Ranger    │
│ ┌────┐ ┌────┐   │ │ +5 to hit           │ │ Alignment: CG    │
│ │STR │ │DEX │   │ │ 1d8+3 piercing      │ │                  │
│ │ 14 │ │ 16 │   │ │ [🎲 Attack Roll]    │ │ Description...   │
│ │+2🎲│ │+3🎲│   │ │ [🎲 Damage Roll]    │ │                  │
│ └────┘ └────┘   │ └─────────────────────┘ │ 🎒 INVENTORY     │
│ ┌────┐ ┌────┐   │                          │                  │
│ │CON │ │INT │   │ 🛡️ DEFENSE              │ • Rope (50 ft)   │
│ │ 12 │ │ 10 │   │                          │ • Rations x5     │
│ │+1🎲│ │+0🎲│   │ AC: 16 (Leather)         │ • Torches x3     │
│ └────┘ └────┘   │ Armor Type: Light        │                  │
│ ┌────┐ ┌────┐   │                          │ 📍 LOCATION      │
│ │WIS │ │CHA │   │ 💚 RESOURCES             │                  │
│ │ 15 │ │  8 │   │                          │ Region: Forest   │
│ │+2🎲│ │-1🎲│   │ HP: ████████░░ 34/40    │ Coords: (10,20)  │
│ └────┘ └────┘   │     [Quick Heal ❤️]      │                  │
│                  │                          │                  │
│ 🎯 SKILLS        │ ✨ ABILITIES             │                  │
│                  │                          │                  │
│ ✓ Perception +5🎲│ • Hunter's Mark         │                  │
│ ✓ Stealth    +5🎲│ • Favored Enemy         │                  │
│ ✓ Survival   +4🎲│                          │                  │
│   Athletics  +2🎲│                          │                  │
│   ...            │                          │                  │
│                  │                          │                  │
└──────────────────┴──────────────────────────┴──────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 🎲 RECENT ROLLS                                                 │
│ • d20+3 Perception = 18 (Success!)                             │
│ • 1d8+3 Longbow damage = 7 piercing                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Component Categorization System

### Automatic Component Categorization

The system needs to intelligently categorize components based on:
1. **Component type name** (e.g., "Attributes", "weapon", "health")
2. **Module it came from** (e.g., fantasy_combat, generic_fantasy)
3. **Metadata hints** (if we add category field to UI metadata)
4. **Field analysis** (if it has damage_dice, it's probably a weapon)

### Categories:

#### 1. **CORE** (Always visible, top priority)
- `Attributes` - Large prominent display in left column
- `health` or `Health` - Show as HP bar in header
- `CharacterDetails` - Race/class info in header or right column

#### 2. **COMBAT** (Center column)
- `weapon` - Attack cards with roll buttons
- `armor` - Defense display with AC
- Any component with `damage_dice` field
- Any component with `attack_bonus` field
- Combat-related abilities

#### 3. **SKILLS** (Left column, below attributes)
- `Skills` component
- `Proficiencies` component
- Tool proficiencies
- Languages

#### 4. **RESOURCES** (Center column, prominent)
- `health` - HP tracking with progress bar
- `Magic` or `Spells` - Spell slots
- `Ki`, `Rage`, etc. - Class resources
- Temporary effects/buffs

#### 5. **INVENTORY** (Right column)
- `Inventory` component
- `Container` components
- Item lists
- Equipment

#### 6. **INFO** (Right column)
- `Identity` - Description
- `Position` - Location info
- Background/story
- Notes

#### 7. **MISC** (Right column, bottom)
- Any component that doesn't fit above categories
- Still displayed beautifully with FormBuilder
- Expandable sections to save space

### Category Detection Logic:

```python
def categorize_component(component_type: str, component_data: dict) -> str:
    """Determine which category a component belongs to."""

    # Exact type matches (highest priority)
    core_types = {'Attributes', 'CharacterDetails', 'health', 'Health'}
    combat_types = {'weapon', 'armor', 'Weapon', 'Armor'}
    skill_types = {'Skills', 'Proficiencies'}
    resource_types = {'Magic', 'Spells', 'SpellSlots', 'Ki', 'Rage'}
    inventory_types = {'Inventory', 'Container', 'Equipment'}
    info_types = {'Identity', 'Position', 'Background'}

    if component_type in core_types:
        return 'CORE'
    if component_type in combat_types:
        return 'COMBAT'
    if component_type in skill_types:
        return 'SKILLS'
    if component_type in resource_types:
        return 'RESOURCES'
    if component_type in inventory_types:
        return 'INVENTORY'
    if component_type in info_types:
        return 'INFO'

    # Field-based detection (check component data structure)
    if 'damage_dice' in component_data or 'attack_bonus' in component_data:
        return 'COMBAT'

    if 'current' in component_data and 'max' in component_data:
        # Likely a resource tracker (HP, spell slots, etc.)
        return 'RESOURCES'

    # Default to MISC
    return 'MISC'
```

---

## 🎲 Dice Rolling System

### Roll Types

1. **Ability Checks** - d20 + ability modifier
2. **Skill Checks** - d20 + skill modifier
3. **Saving Throws** - d20 + save modifier
4. **Attack Rolls** - d20 + attack bonus
5. **Damage Rolls** - weapon damage dice + modifier
6. **Initiative** - d20 + dexterity modifier
7. **Custom Rolls** - Any dice notation from component

### Roll Button Placement

Every "rollable" value should have a 🎲 button next to it:

```html
<!-- Attribute -->
<div class="attribute-card">
    <h4>STR</h4>
    <div class="attribute-value">14</div>
    <div class="attribute-modifier">
        +2 <button class="dice-btn" onclick="rollAbilityCheck('strength', 2)">🎲</button>
    </div>
</div>

<!-- Weapon Attack -->
<div class="weapon-card">
    <h4>Longbow</h4>
    <div>+5 to hit <button class="dice-btn" onclick="rollAttack('longbow', 5)">🎲</button></div>
    <div>1d8+3 piercing <button class="dice-btn" onclick="rollDamage('longbow', '1d8+3')">🎲</button></div>
</div>

<!-- Skill -->
<div class="skill-item">
    Perception +5 <button class="dice-btn" onclick="rollSkill('perception', 5)">🎲</button>
</div>
```

### API Endpoint: `/api/roll`

**Request:**
```json
{
    "entity_id": "entity_abc123",
    "roll_type": "ability_check",  // or skill, attack, damage, custom
    "notation": "1d20+3",
    "label": "Strength check",
    "metadata": {
        "ability": "strength",
        "modifier": 3
    }
}
```

**Response:**
```json
{
    "success": true,
    "result": {
        "total": 18,
        "rolls": [15],
        "modifier": 3,
        "notation": "1d20+3",
        "label": "Strength check",
        "timestamp": "2025-11-06T12:34:56Z"
    }
}
```

### Roll Result Display

**Option 1: Toast Notification** (non-blocking)
```
┌────────────────────────────────────┐
│ 🎲 Strength Check                 │
│                                    │
│ d20: [15] + 3 = 18                │
│                                    │
│ ✅ Result: 18                      │
└────────────────────────────────────┘
```

**Option 2: Roll Log Section** (persistent)
- Show recent rolls at bottom of sheet
- Expandable log of all rolls
- Color-coded by type
- Shows timestamp

**Option 3: Modal** (blocking, for important rolls)
- Large dramatic display
- Animated dice roll
- Show critical success/fail
- For initiative, important saves

### Roll Event Logging

Every roll should be logged as an event:
```python
engine.log_event(
    event_type='roll.completed',
    entity_id=character_id,
    data={
        'roll_type': 'ability_check',
        'ability': 'strength',
        'notation': '1d20+3',
        'result': 18,
        'rolls': [15],
        'modifier': 3
    }
)
```

---

## 🎨 Component-Specific Renderers

### 1. Attributes Renderer (Special Case)

**Location**: Left column, top, prominent
**Display**:
- 2x3 grid of large cards
- Score, modifier, and dice button
- Click card to roll ability check
- Color-coded by value (red < 10, yellow 10-14, green 15+)

```html
<div class="attributes-section">
    <h3>ATTRIBUTES</h3>
    <div class="attributes-grid">
        <div class="attribute-card strength" data-score="14">
            <div class="attribute-label">STR</div>
            <div class="attribute-score">14</div>
            <div class="attribute-modifier" onclick="rollAbilityCheck('strength', 2)">
                +2 🎲
            </div>
        </div>
        <!-- Repeat for DEX, CON, INT, WIS, CHA -->
    </div>
</div>
```

### 2. Weapon Renderer

**Location**: Center column, combat section
**Display**:
- Card per weapon
- Attack bonus with roll button
- Damage with roll button
- Properties (range, damage type, etc.)

```html
<div class="weapon-card">
    <div class="weapon-header">
        <h4>⚔️ Longbow</h4>
        <span class="weapon-range">Range</span>
    </div>
    <div class="weapon-attack">
        <span>Attack: +5</span>
        <button class="dice-btn-lg" onclick="rollAttack('longbow')">
            🎲 Attack
        </button>
    </div>
    <div class="weapon-damage">
        <span>Damage: 1d8+3 piercing</span>
        <button class="dice-btn-lg" onclick="rollDamage('longbow')">
            🎲 Damage
        </button>
    </div>
</div>
```

### 3. Health Renderer

**Location**: Header quick stats OR center column
**Display**:
- Current / Max
- Progress bar (visual health)
- Quick heal/damage buttons
- Death saves if at 0 HP

```html
<div class="health-display">
    <h4>❤️ Hit Points</h4>
    <div class="hp-bar-container">
        <div class="hp-bar" style="width: 85%"></div>
        <span class="hp-text">34 / 40</span>
    </div>
    <div class="hp-actions">
        <button onclick="adjustHP(-5)">➖ Damage</button>
        <button onclick="adjustHP(5)">➕ Heal</button>
    </div>
</div>
```

### 4. Skills Renderer

**Location**: Left column, below attributes
**Display**:
- Compact list
- Proficiency indicator (✓)
- Modifier + dice button
- Collapsible groups (by ability)

```html
<div class="skills-section">
    <h3>🎯 SKILLS</h3>
    <div class="skill-group">
        <h4>Strength</h4>
        <div class="skill-item proficient">
            <span>✓ Athletics</span>
            <span>+4 <button class="dice-btn-sm">🎲</button></span>
        </div>
    </div>
    <!-- Repeat for other ability groups -->
</div>
```

### 5. Armor Renderer

**Location**: Center column, defense section
**Display**:
- AC prominently
- Armor type
- Special properties

```html
<div class="defense-display">
    <h4>🛡️ ARMOR CLASS</h4>
    <div class="ac-value">16</div>
    <div class="armor-details">
        <span>Type: Light Armor</span>
        <span>Armor: Leather</span>
    </div>
</div>
```

### 6. Magic/Spells Renderer

**Location**: Center column, resources section
**Display**:
- Spell slots by level (checkboxes to track usage)
- Known spells list
- Cast spell buttons with save DC

```html
<div class="magic-display">
    <h4>✨ SPELL SLOTS</h4>
    <div class="spell-slots">
        <div class="slot-level">
            <span>Level 1:</span>
            <div class="slot-tracker">
                <input type="checkbox" checked> <!-- Used -->
                <input type="checkbox" checked>
                <input type="checkbox">
                <input type="checkbox"> <!-- Available -->
            </div>
        </div>
    </div>
    <div class="known-spells">
        <h5>Known Spells</h5>
        <ul>
            <li>Hunter's Mark (1st)</li>
            <li>Cure Wounds (1st)</li>
        </ul>
    </div>
</div>
```

### 7. Inventory Renderer

**Location**: Right column
**Display**:
- Item list with icons
- Weight tracking
- Quick equip/use buttons

```html
<div class="inventory-section">
    <h4>🎒 INVENTORY</h4>
    <div class="inventory-list">
        <div class="inventory-item">
            <span>Rope, hempen (50 feet)</span>
            <span class="item-weight">10 lb</span>
        </div>
        <!-- More items -->
    </div>
    <div class="weight-total">
        Total: 45 / 150 lb
    </div>
</div>
```

### 8. Fallback Renderer (Unknown Components)

**Location**: Right column, MISC section
**Display**:
- Use FormBuilder.build_display()
- Collapsible sections to save space
- Still looks professional

```html
<div class="misc-section">
    <details class="component-collapsible">
        <summary>
            <h4>CustomComponent</h4>
            <span class="expand-icon">▼</span>
        </summary>
        <div class="component-content">
            {{ form_builder.build_display(component_type, data) }}
        </div>
    </details>
</div>
```

---

## 🏗️ Implementation Plan

### Phase 1: Backend - Dice Rolling API ✅ (RNG module exists!)

**Actually... we already have this!** The RNG module:
- Has DiceParser for parsing dice notation
- Has roll.requested / roll.completed events
- Just needs an API endpoint wrapper

**New Endpoint:** `/api/roll`
```python
@app.route('/api/roll', methods=['POST'])
def api_roll():
    """Roll dice for a character action."""
    data = request.json
    entity_id = data.get('entity_id')
    notation = data.get('notation')  # e.g., "1d20+3"
    roll_type = data.get('roll_type')  # ability_check, attack, etc.
    label = data.get('label', 'Roll')

    engine = get_engine()

    # Publish roll.requested event
    engine.publish_event(Event(
        event_type='roll.requested',
        entity_id=entity_id,
        data={
            'roll_type': roll_type,
            'notation': notation,
            'metadata': data.get('metadata', {})
        }
    ))

    # The RNG system will process and publish roll.completed
    # For now, parse and roll directly
    from src.modules.rng.dice_parser import DiceParser
    parser = DiceParser()
    result = parser.parse_and_roll(notation)

    return jsonify({
        'success': True,
        'result': {
            'total': result['total'],
            'rolls': result['rolls'],
            'modifier': result.get('modifier', 0),
            'notation': notation,
            'label': label
        }
    })
```

### Phase 2: Frontend - Layout Redesign

**File**: `src/web/templates/client/character_sheet.html`

1. **New 3-column CSS Grid layout**
2. **Header with quick stats bar**
3. **Component categorization function**
4. **Render components in appropriate columns**

### Phase 3: Component Renderers

**File**: `src/web/character_renderers.py` (new)

Create specialized renderers:
```python
class ComponentRenderer:
    def render_attributes(self, data):
        # Return HTML for attributes cards with dice buttons

    def render_weapon(self, data):
        # Return HTML for weapon card with attack/damage rolls

    def render_health(self, data):
        # Return HTML for HP bar with quick actions

    # ... etc
```

Or use Jinja macros in template.

### Phase 4: JavaScript Interactivity

**File**: Character sheet template `<script>` section

```javascript
async function rollAbilityCheck(ability, modifier) {
    const response = await fetch('/api/roll', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            entity_id: characterId,
            notation: `1d20+${modifier}`,
            roll_type: 'ability_check',
            label: `${ability.charAt(0).toUpperCase() + ability.slice(1)} Check`,
            metadata: {ability: ability, modifier: modifier}
        })
    });

    const result = await response.json();
    showRollResult(result);
}

function showRollResult(result) {
    // Display in toast/modal/log
    const toast = document.createElement('div');
    toast.className = 'roll-toast';
    toast.innerHTML = `
        <strong>${result.result.label}</strong><br>
        🎲 ${result.result.notation} = ${result.result.total}
    `;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 5000);
}
```

### Phase 5: Polish & Testing

- Responsive design (mobile-friendly)
- Accessibility (keyboard navigation, screen readers)
- Loading states
- Error handling
- Animation/transitions
- Theme consistency

---

## 📐 Technical Specifications

### CSS Grid Layout

```css
.character-sheet-layout {
    display: grid;
    grid-template-columns: 300px 1fr 350px;
    grid-template-rows: auto 1fr;
    gap: 1.5rem;
}

.character-header {
    grid-column: 1 / -1;
}

.left-column { /* Stats & Checks */ }
.center-column { /* Combat & Actions */ }
.right-column { /* Info & Inventory */ }

@media (max-width: 1200px) {
    .character-sheet-layout {
        grid-template-columns: 1fr 1fr;
    }
    .right-column {
        grid-column: 1 / -1;
    }
}

@media (max-width: 768px) {
    .character-sheet-layout {
        grid-template-columns: 1fr;
    }
}
```

### Component Metadata Extension

Add `category` hint to UI metadata:
```python
def get_ui_metadata(self):
    return {
        '__category__': 'COMBAT',  # Optional hint for renderer
        'damage_dice': {
            'label': 'Damage',
            'widget': 'text',
            'rollable': True,  # NEW: Indicates this can be rolled
            'roll_type': 'damage'
        }
    }
```

### Roll Result Event

```python
{
    'event_type': 'roll.completed',
    'entity_id': 'entity_abc123',
    'timestamp': '2025-11-06T12:34:56Z',
    'data': {
        'roll_type': 'ability_check',
        'ability': 'strength',
        'notation': '1d20+2',
        'result': 18,
        'rolls': [16],
        'modifier': 2,
        'success': True,  # If DC was checked
        'dc': 15
    }
}
```

---

## 🎯 Success Criteria

### Must Have:
- ✅ 3-column responsive layout
- ✅ Components automatically categorized
- ✅ Attributes prominently displayed with dice buttons
- ✅ Weapons show attack and damage roll buttons
- ✅ Dice rolling works for all rollable fields
- ✅ Roll results displayed clearly
- ✅ Unknown components still display nicely (fallback)
- ✅ Mobile responsive

### Should Have:
- ✅ HP tracking with visual progress bar
- ✅ Skill list with proficiency indicators
- ✅ Armor/AC display
- ✅ Inventory list
- ✅ Roll history log
- ✅ Collapsible sections for misc components

### Nice to Have:
- ✅ Animated dice rolls
- ✅ Critical hit/fail detection
- ✅ Advantage/disadvantage rolls
- ✅ Quick HP adjustment buttons
- ✅ Spell slot tracking
- ✅ Resource management

---

## 🚧 Risks & Mitigations

### Risk 1: Too Many Components = Cluttered
**Mitigation**:
- Collapsible sections for MISC
- Priority-based rendering (core always visible)
- Pagination for long lists (skills, spells)

### Risk 2: Mobile Performance
**Mitigation**:
- Lazy load non-visible sections
- Use CSS Grid's responsive features
- Minimize JavaScript for rolls

### Risk 3: Module Compatibility
**Mitigation**:
- Fallback renderer for unknown types
- Optional category hints in UI metadata
- Graceful degradation

---

## 📝 Next Steps

1. **Review & Approve** - Get feedback on this design
2. **Backend First** - Implement `/api/roll` endpoint
3. **Layout Second** - Create new 3-column layout
4. **Renderers Third** - Build component-specific renderers
5. **Interactivity Fourth** - Add dice rolling JavaScript
6. **Polish Fifth** - Responsive, accessible, beautiful

---

## 🎲 Example: Complete Character Sheet

**Character**: Gandara Swiftblade (Level 3 Elf Ranger)

**Components**:
- Attributes (STR 14, DEX 16, CON 12, INT 10, WIS 15, CHA 8)
- Identity (Description)
- Position (Forest location)
- PlayerCharacter (marker)
- weapon (Longbow, 1d8+3 piercing)
- armor (Leather, AC 14)
- Health (34/40 HP) *(future)*
- Skills (Perception +5, Stealth +5, Survival +4) *(future)*

**Rendering**:
```
┌──────────────────────────────────────────────────────────────────┐
│ GANDARA SWIFTBLADE                                               │
│ Level 3 Elf Ranger                                               │
│ ❤️ 34/40 HP  🛡️ AC 14  ⚡ +3 Initiative  🎯 +2 Proficiency      │
└──────────────────────────────────────────────────────────────────┘

┌────────────────┬────────────────────────┬─────────────────────┐
│ ATTRIBUTES     │ ⚔️ WEAPONS             │ 📜 CHARACTER        │
│                │                        │                     │
│ STR 14 +2 🎲  │ Longbow                │ Race: Elf           │
│ DEX 16 +3 🎲  │ Attack: +5 🎲          │ Class: Ranger       │
│ CON 12 +1 🎲  │ Damage: 1d8+3 🎲       │ Alignment: CG       │
│ INT 10 +0 🎲  │                        │                     │
│ WIS 15 +2 🎲  │ 🛡️ DEFENSE             │ A fierce elf        │
│ CHA  8 -1 🎲  │                        │ ranger from the     │
│                │ AC: 14                 │ Moonwood...         │
│ 🎯 SKILLS      │ Armor: Leather (Light) │                     │
│                │                        │ 📍 LOCATION         │
│ Perception +5🎲│ ❤️ HIT POINTS          │                     │
│ Stealth +5 🎲  │ ████████░░ 34/40      │ Region: Forest      │
│ Survival +4 🎲 │                        │                     │
└────────────────┴────────────────────────┴─────────────────────┘

Recent Rolls:
• 🎲 DEX Check: d20(15)+3 = 18
• 🎲 Longbow Attack: d20(12)+5 = 17 (HIT!)
• 🎲 Longbow Damage: 1d8(6)+3 = 9 piercing
```

This design gives players:
- Quick access to stats
- One-click dice rolling
- Organized information
- Room for future components
- Professional appearance

---

**End of Design Document**
