# Spell Data Files

This directory contains spell data in JSON format. Spells are **data-driven**, not hardcoded, allowing DMs to:

- Add custom spells at campaign start
- Create new spells during gameplay
- Export spell lists to share with other campaigns
- Modify or ban existing spells

## Quick Start

### Loading Starter Spells

```python
from src.modules.generic_fantasy.spell_utils import load_spells_from_file

# Load the included starter spells
load_spells_from_file(engine, 'data/spells/starter_spells.json')
```

### Adding a Custom Spell

```python
from src.modules.generic_fantasy.spell_utils import add_spell

add_spell(engine, 'eldritch_blast', 'Eldritch Blast - Warlock cantrip', {
    'level': 0,
    'school': 'evocation',
    'damage': '1d10',
    'damage_type': 'force',
    'range': '120 feet',
    'components': ['V', 'S']
})
```

### Exporting Campaign Spells

```python
from src.modules.generic_fantasy.spell_utils import export_spells_to_file

# Export all spells to backup or share
export_spells_to_file(engine, 'data/spells/my_campaign_spells.json')
```

## JSON Format

Spell files use this format:

```json
{
  "spells": [
    {
      "key": "fireball",
      "description": "Fireball - 8d6 fire damage in 20ft radius",
      "metadata": {
        "level": 3,
        "school": "evocation",
        "damage": "8d6",
        "damage_type": "fire",
        "range": "150 feet",
        "area": "20ft radius",
        "components": ["V", "S", "M"]
      }
    }
  ]
}
```

### Required Fields

- `key` - Unique identifier (lowercase, underscores)
- `description` - Human-readable name and summary
- `metadata.level` - Spell level (0-9, where 0 = cantrip)
- `metadata.school` - School of magic

### Optional Metadata Fields

- `damage` - Damage dice (e.g., "8d6", "2d10+5")
- `damage_type` - Type of damage (fire, cold, lightning, etc.)
- `healing` - Healing dice for healing spells
- `range` - Spell range (e.g., "120 feet", "Touch", "Self")
- `area` - Area of effect (e.g., "20ft radius", "30ft cone")
- `components` - Array of components: "V" (verbal), "S" (somatic), "M" (material)
- `ritual` - Boolean, can be cast as ritual
- `concentration` - Boolean, requires concentration
- `duration` - How long spell lasts
- `casting_time` - Action, bonus action, reaction, etc.
- `reaction` - Boolean, cast as reaction
- `bonus_action` - Boolean, cast as bonus action
- `utility` - Boolean, primarily utility spell
- `control` - Boolean, primarily control/crowd control
- `ac_bonus` - For defensive spells (e.g., Shield = 5)

## Querying Spells

```python
from src.modules.generic_fantasy.spell_utils import (
    get_spells_by_level,
    get_spells_by_school
)

# Get all cantrips
cantrips = get_spells_by_level(engine, 0)

# Get all evocation spells
evocation_spells = get_spells_by_school(engine, 'evocation')

# Get all spells (from registry)
spells_registry = engine.create_registry('spells', 'generic_fantasy')
all_spells = spells_registry.get_all()
```

## Schools of Magic

Standard schools:
- `abjuration` - Protection, wards, shields
- `conjuration` - Summoning, teleportation
- `divination` - Information, detection
- `enchantment` - Mind control, charm
- `evocation` - Energy, damage
- `illusion` - Deception, tricks
- `necromancy` - Death, undead
- `transmutation` - Transformation, alteration

## Example: Campaign-Specific Spells

Create `my_campaign_spells.json`:

```json
{
  "spells": [
    {
      "key": "arcane_explosion",
      "description": "Arcane Explosion - Custom AoE spell",
      "metadata": {
        "level": 4,
        "school": "evocation",
        "damage": "6d8",
        "damage_type": "force",
        "range": "60 feet",
        "area": "15ft radius",
        "components": ["V", "S", "M"],
        "custom": true,
        "notes": "Created for the Stormhaven campaign"
      }
    }
  ]
}
```

Then load it:

```python
load_spells_from_file(engine, 'data/spells/my_campaign_spells.json')
```

## Best Practices

1. **Keep starter spells unchanged** - Copy `starter_spells.json` before modifying
2. **Use descriptive keys** - `arcane_missile` not `am` or `spell_1`
3. **Document custom spells** - Add `notes` field explaining the spell
4. **Version your spell files** - Use git or backups
5. **Export regularly** - Back up campaign spells with `export_spells_to_file()`

## Integration with Magic Component

Characters' known spells reference these spell keys:

```python
# Character's Magic component
{
    'spellcasting_ability': 'intelligence',
    'cantrips': ['fire_bolt', 'mage_hand'],  # Spell keys
    'known_spells': ['fireball', 'shield', 'arcane_explosion'],  # Includes custom!
    'prepared_spells': ['fireball', 'shield']
}
```

The spell registry provides the full spell data when needed.
