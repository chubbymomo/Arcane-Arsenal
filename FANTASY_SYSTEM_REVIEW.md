# Fantasy System Integration Review

## Current State

### ✅ Implemented Components

#### generic_fantasy module:
- **AttributesComponent**: STR, DEX, CON, INT, WIS, CHA with modifiers
- **CharacterDetailsComponent**: Race, class, background, alignment, level
- **SkillsComponent**: 18 skills with proficiency and expertise
- **ExperienceComponent**: XP tracking with level progression
- **MagicComponent**: Spell slots, cantrips, known/prepared spells

#### fantasy_combat module:
- **HealthComponent**: HP tracking with temp HP
- **ArmorComponent**: AC and armor types
- **WeaponComponent**: Damage dice, damage type, attack bonus

#### items module:
- **ItemComponent**: Weight, value, rarity, quantity
- **EquippableComponent**: Slots, requirements (STR, level)
- **ConsumableComponent**: Charges and effects
- Equipment system with validation

### ❌ Missing Integration Points

#### 1. **Class-to-Magic Integration**
**Problem**: Classes don't indicate if they're spellcasters
- Wizard, Cleric, Bard should be spellcasters
- Fighter, Rogue, Barbarian are not
- No metadata in class registry about spellcasting ability

**Solution Needed**:
```python
classes.register('wizard', 'Wizard - Scholar of arcane magic', {
    'hit_die': 'd10',
    'primary_ability': 'intelligence',
    'saves': ['intelligence', 'wisdom'],
    'spellcaster': True,              # NEW
    'spellcasting_ability': 'intelligence',  # NEW
    'spell_progression': 'full'       # NEW: full, half, third, none
})
```

#### 2. **Automatic Component Addition**
**Problem**: When creating a character with a spellcasting class, Magic component isn't auto-added

**Solution Needed**: Event listener on `CharacterDetails` component addition:
- If class is spellcaster → auto-add Magic component
- Set spellcasting_ability based on class metadata
- Initialize spell slots based on level and spell progression

#### 3. **Spell Slot Progression Tables**
**Problem**: No system for calculating spell slots by level/class

**Solution Needed**: Add spell slot progression data:
```python
# Full casters (Wizard, Cleric, Bard)
FULL_CASTER_SLOTS = {
    1: {"1": 2},
    2: {"1": 3},
    3: {"1": 4, "2": 2},
    # ... etc
}

# Half casters (Paladin, Ranger)
HALF_CASTER_SLOTS = {...}
```

#### 4. **Spell Entities vs Spell Strings**
**Current**: Spells are strings in Magic component
**Missing**: Spells as entities with their own components

**Decision Point**:
- **Option A**: Keep spells as strings (simpler, current approach)
- **Option B**: Make spells entities with Spell component (more flexible)

**Recommendation**: Keep as strings for now (simpler), add spell entities later if needed

#### 5. **Class Features & Abilities**
**Problem**: No component for class features (Rage, Sneak Attack, etc.)

**Solution Needed**: New component type
```python
class ClassFeaturesComponent:
    schema = {
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "uses_per_rest": {"type": "integer"},
                    "current_uses": {"type": "integer"}
                }
            }
        }
    }
```

#### 6. **Proficiency Bonus by Level**
**Problem**: Skills component has proficiency_bonus but it's not auto-calculated from level

**Solution**: Add to CharacterDetails or calculate dynamically:
```python
def calculate_proficiency_bonus(level: int) -> int:
    return 2 + ((level - 1) // 4)  # +2 at 1, +3 at 5, +4 at 9, etc.
```

#### 7. **Saving Throws**
**Problem**: Classes have 'saves' metadata but no component tracks saving throw proficiencies

**Solution Needed**: Either:
- Add to Skills component
- Create separate SavingThrows component
- Add to Attributes display

#### 8. **Spell Registry**
**Current**: Known spells are free-form strings
**Missing**: Spell registry with spell data

**Solution Needed**:
```python
spells = engine.create_registry('spells', 'generic_fantasy')
spells.register('fireball', 'Fireball - 8d6 fire damage in 20ft radius', {
    'level': 3,
    'school': 'evocation',
    'damage': '8d6',
    'damage_type': 'fire'
})
```

## Priority Recommendations

### ✅ HIGH Priority (Essential for playability) - COMPLETED
1. ✅ **Add required_level check to equipment system** - DONE
2. ✅ **Add spellcasting metadata to class registry** - DONE
3. ✅ **Add proficiency bonus calculation** - DONE
4. ✅ **Auto-add Magic component for spellcasting classes** - DONE
5. ✅ **Add spell slot progression tables** - DONE

### MEDIUM Priority (Enhances gameplay) - IN PROGRESS
6. **Add saving throws tracking** - Next
7. **Add spell registry** - Next
8. **Add common spell list**

### LOW Priority (Nice to have)
9. **Class features component**
10. **Spell entities (vs strings)**
11. **Multi-classing support**

## Implementation Philosophy Check

All components follow ECS principles:
- ✅ Pure data, no behavior
- ✅ Composition over inheritance
- ✅ Registry-based validation
- ✅ Loose coupling via StateEngine
- ✅ Event-driven integration

## Next Steps

Recommend implementing HIGH priority items:
1. Enhance class registry metadata
2. Add event listener for auto-Magic component
3. Calculate proficiency bonus from level
4. Add spell progression helper functions
