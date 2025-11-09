"""
Magic Component for Generic Fantasy Module.

Provides spellcasting capabilities including spell slots and known spells.
"""

from typing import Dict, Any, List
from ..base import ComponentTypeDefinition


class MagicComponent(ComponentTypeDefinition):
    """
    Spellcasting component for magic users.

    Tracks spell slots (current/max for each level), known spells, and
    spellcasting ability. Follows standard fantasy RPG spellcasting systems.
    """

    type = "Magic"
    description = "Spellcasting ability, spell slots, and known spells"
    schema_version = "1.0.0"
    module = "generic_fantasy"

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for magic."""
        return {
            "type": "object",
            "properties": {
                "spellcasting_ability": {
                    "type": "string",
                    "enum": ["intelligence", "wisdom", "charisma"],
                    "description": "Ability used for spellcasting (INT, WIS, or CHA)"
                },
                "spell_slots": {
                    "type": "object",
                    "description": "Spell slots by level (1-9)",
                    "properties": {
                        "1": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}},
                        "2": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}},
                        "3": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}},
                        "4": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}},
                        "5": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}},
                        "6": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}},
                        "7": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}},
                        "8": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}},
                        "9": {"type": "object", "properties": {"current": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}}
                    },
                    "default": {}
                },
                "known_spells": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of spells the character knows",
                    "default": []
                },
                "prepared_spells": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of spells the character has prepared",
                    "default": []
                },
                "cantrips": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of cantrips (level 0 spells)",
                    "default": []
                }
            },
            "required": ["spellcasting_ability"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Return UI metadata for magic."""
        return {
            "spellcasting_ability": {
                "label": "Spellcasting Ability",
                "widget": "text",
                "order": 0,
                "help_text": "Ability score used for spellcasting (intelligence, wisdom, or charisma)",
                "placeholder": "intelligence"
            },
            "spell_slots": {
                "label": "Spell Slots",
                "widget": "textarea",
                "order": 1,
                "help_text": "Spell slots per level (JSON format: {\"1\": {\"current\": 4, \"max\": 4}})",
                "placeholder": "{\"1\": {\"current\": 4, \"max\": 4}, \"2\": {\"current\": 3, \"max\": 3}}"
            },
            "cantrips": {
                "label": "Cantrips",
                "widget": "textarea",
                "order": 2,
                "help_text": "Cantrips known (one per line or comma-separated)",
                "placeholder": "Fire Bolt, Mage Hand, Prestidigitation"
            },
            "known_spells": {
                "label": "Known Spells",
                "widget": "textarea",
                "order": 3,
                "help_text": "Spells known (one per line or comma-separated)",
                "placeholder": "Magic Missile, Shield, Fireball"
            },
            "prepared_spells": {
                "label": "Prepared Spells",
                "widget": "textarea",
                "order": 4,
                "help_text": "Spells currently prepared (one per line or comma-separated)",
                "placeholder": "Magic Missile, Shield, Detect Magic"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Magic appears in the RESOURCES category."""
        return {
            "visible": True,
            "category": "resources",
            "priority": 1,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer for magic with spell slot tracking."""
        from markupsafe import escape

        spellcasting_ability = data.get('spellcasting_ability', 'intelligence')
        spell_slots = data.get('spell_slots', {})
        cantrips = data.get('cantrips', [])
        known_spells = data.get('known_spells', [])
        prepared_spells = data.get('prepared_spells', [])

        # Calculate spell save DC and attack bonus if we have the entity
        spell_save_dc = None
        spell_attack_bonus = None
        proficiency_bonus = 2  # default

        if engine and entity_id:
            # Get attributes
            attributes = engine.get_component(entity_id, 'Attributes')
            if attributes:
                ability_score = attributes.data.get(spellcasting_ability, 10)
                ability_mod = (ability_score - 10) // 2

                # Try to get proficiency bonus from Skills component
                skills = engine.get_component(entity_id, 'Skills')
                if skills:
                    proficiency_bonus = skills.data.get('proficiency_bonus', 2)

                spell_save_dc = 8 + proficiency_bonus + ability_mod
                spell_attack_bonus = proficiency_bonus + ability_mod

        html = ['<div class="magic-display">']

        # Spellcasting ability and stats
        ability_display = spellcasting_ability.upper()[:3]
        html.append('<div class="spell-stats" style="margin-bottom: 1rem;">')
        html.append(f'<p><strong>Spellcasting Ability:</strong> {ability_display}</p>')

        if spell_save_dc is not None and spell_attack_bonus is not None:
            attack_str = f"+{spell_attack_bonus}" if spell_attack_bonus >= 0 else str(spell_attack_bonus)
            html.append(f'<p><strong>Spell Save DC:</strong> {spell_save_dc} | <strong>Spell Attack:</strong> {attack_str}</p>')

        html.append('</div>')

        # Spell slots
        if spell_slots:
            html.append('<div class="spell-slots" style="margin-bottom: 1rem;">')
            html.append('<h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--primary-color);">Spell Slots</h4>')

            for level in range(1, 10):
                level_str = str(level)
                if level_str in spell_slots:
                    slot_data = spell_slots[level_str]
                    current = slot_data.get('current', 0)
                    maximum = slot_data.get('max', 0)

                    if maximum > 0:
                        # Create visual slot indicators
                        slots_html = []
                        for i in range(maximum):
                            if i < current:
                                slots_html.append('🔮')  # filled slot
                            else:
                                slots_html.append('⚪')  # empty slot

                        html.append(f'''
                            <div class="spell-slot-level" style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                                <span style="min-width: 4rem; font-weight: 600;">Level {level}:</span>
                                <span style="font-size: 1.1rem;">{' '.join(slots_html)}</span>
                                <span style="color: var(--text-muted); font-size: 0.9rem;">({current}/{maximum})</span>
                            </div>
                        ''')

            html.append('</div>')

        # Cantrips
        if cantrips:
            html.append('<div class="cantrips" style="margin-bottom: 1rem;">')
            html.append('<h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--primary-color);">Cantrips</h4>')
            html.append('<ul style="margin: 0; padding-left: 1.5rem;">')
            for cantrip in cantrips:
                html.append(f'<li>{escape(cantrip)}</li>')
            html.append('</ul>')
            html.append('</div>')

        # Known spells
        if known_spells:
            html.append('<div class="known-spells" style="margin-bottom: 1rem;">')
            html.append('<h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--primary-color);">Known Spells</h4>')
            html.append('<ul style="margin: 0; padding-left: 1.5rem; column-count: 2; column-gap: 1rem;">')
            for spell in known_spells:
                is_prepared = spell in prepared_spells
                marker = '📖 ' if is_prepared else ''
                html.append(f'<li>{marker}{escape(spell)}</li>')
            html.append('</ul>')
            if prepared_spells:
                html.append('<p style="margin-top: 0.5rem; font-size: 0.85rem; color: var(--text-muted);">📖 = Prepared</p>')
            html.append('</div>')

        # Prepared spells (if different from known)
        elif prepared_spells:
            html.append('<div class="prepared-spells" style="margin-bottom: 1rem;">')
            html.append('<h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--primary-color);">Prepared Spells</h4>')
            html.append('<ul style="margin: 0; padding-left: 1.5rem;">')
            for spell in prepared_spells:
                html.append(f'<li>{escape(spell)}</li>')
            html.append('</ul>')
            html.append('</div>')

        html.append('</div>')
        return ''.join(html)

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """
        Validate spellcasting ability and spell slot structure.

        Args:
            data: Component data to validate
            engine: StateEngine instance

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        ability = data.get('spellcasting_ability')
        if ability not in ['intelligence', 'wisdom', 'charisma']:
            raise ValueError(
                f"Invalid spellcasting_ability '{ability}'. "
                f"Must be 'intelligence', 'wisdom', or 'charisma'"
            )

        # Validate spell slots structure
        spell_slots = data.get('spell_slots', {})
        for level_str, slot_data in spell_slots.items():
            # Check level is 1-9
            try:
                level = int(level_str)
                if level < 1 or level > 9:
                    raise ValueError(f"Spell slot level must be 1-9, got {level}")
            except ValueError:
                raise ValueError(f"Spell slot level must be a number 1-9, got '{level_str}'")

            # Check slot_data has current and max
            if not isinstance(slot_data, dict):
                raise ValueError(f"Spell slot data for level {level} must be an object with 'current' and 'max'")

            current = slot_data.get('current')
            maximum = slot_data.get('max')

            if current is None or maximum is None:
                raise ValueError(f"Spell slot level {level} must have 'current' and 'max' values")

            if current < 0 or maximum < 0:
                raise ValueError(f"Spell slot values cannot be negative")

            if current > maximum:
                raise ValueError(f"Current spell slots ({current}) cannot exceed max ({maximum}) for level {level}")

        # Validate prepared spells are subset of known spells
        known = set(data.get('known_spells', []))
        prepared = set(data.get('prepared_spells', []))

        if not prepared.issubset(known) and known:  # Only validate if known_spells is specified
            unknown_prepared = prepared - known
            raise ValueError(
                f"Cannot prepare spells that are not known: {', '.join(unknown_prepared)}"
            )

        return True
