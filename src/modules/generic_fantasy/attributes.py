"""
Attributes Component for Generic Fantasy Module.

Provides core ability scores (Strength, Dexterity, Constitution,
Intelligence, Wisdom, Charisma) commonly used in fantasy RPGs.
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class AttributesComponent(ComponentTypeDefinition):
    """
    Core ability scores for fantasy characters.

    Tracks six attributes (STR, DEX, CON, INT, WIS, CHA) with values typically
    ranging from 1-20 in most fantasy systems. Modifiers are calculated as:
    (attribute - 10) // 2
    """

    type = "Attributes"
    description = "Core ability scores (STR, DEX, CON, INT, WIS, CHA)"
    schema_version = "1.0.0"
    module = "generic_fantasy"

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for attributes."""
        return {
            "type": "object",
            "properties": {
                "strength": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Physical power and muscle"
                },
                "dexterity": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Agility, reflexes, and balance"
                },
                "constitution": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Endurance and health"
                },
                "intelligence": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Reasoning and memory"
                },
                "wisdom": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Awareness and insight"
                },
                "charisma": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Force of personality and leadership"
                },
                "saving_throw_proficiencies": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
                    },
                    "default": [],
                    "description": "Saving throws the character is proficient in"
                }
            },
            "required": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Return UI metadata for attributes."""
        return {
            "strength": {
                "label": "Strength (STR)",
                "widget": "number",
                "order": 0,
                "help_text": "Physical power, muscle, carrying capacity",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Physical Attributes"
            },
            "dexterity": {
                "label": "Dexterity (DEX)",
                "widget": "number",
                "order": 1,
                "help_text": "Agility, reflexes, balance, coordination",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Physical Attributes"
            },
            "constitution": {
                "label": "Constitution (CON)",
                "widget": "number",
                "order": 2,
                "help_text": "Endurance, health, stamina, vitality",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Physical Attributes"
            },
            "intelligence": {
                "label": "Intelligence (INT)",
                "widget": "number",
                "order": 3,
                "help_text": "Reasoning, memory, learning ability",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Mental Attributes"
            },
            "wisdom": {
                "label": "Wisdom (WIS)",
                "widget": "number",
                "order": 4,
                "help_text": "Awareness, intuition, insight, perception",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Mental Attributes"
            },
            "charisma": {
                "label": "Charisma (CHA)",
                "widget": "number",
                "order": 5,
                "help_text": "Force of personality, leadership, persuasion",
                "min": 1,
                "max": 30,
                "step": 1,
                "group": "Mental Attributes"
            },
            "saving_throw_proficiencies": {
                "label": "Saving Throw Proficiencies",
                "widget": "textarea",
                "order": 6,
                "help_text": "Saving throws this character is proficient in (comma-separated: strength, dexterity, etc.)",
                "placeholder": "strength, constitution",
                "group": "Saving Throws"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Attributes appear prominently in the CORE category."""
        return {
            "visible": True,
            "category": "core",
            "priority": 1,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer showing attributes in a grid with modifiers and dice rolling."""
        from markupsafe import escape

        attributes = [
            ('strength', 'STR'),
            ('dexterity', 'DEX'),
            ('constitution', 'CON'),
            ('intelligence', 'INT'),
            ('wisdom', 'WIS'),
            ('charisma', 'CHA')
        ]

        # Get saving throw proficiencies and proficiency bonus
        save_profs = data.get('saving_throw_proficiencies', [])
        proficiency_bonus = 2  # default
        if engine and entity_id:
            skills = engine.get_component(entity_id, 'Skills')
            if skills:
                proficiency_bonus = skills.data.get('proficiency_bonus', 2)

        html = ['<div class="attributes-and-saves">']

        # Attributes Grid
        html.append('<div class="attributes-grid">')

        for attr_key, attr_label in attributes:
            score = data.get(attr_key, 10)
            mod = self.calculate_modifier(score)
            mod_str = f"+{mod}" if mod >= 0 else str(mod)

            # Dice button if entity_id provided
            dice_btn = ''
            if entity_id:
                dice_btn = f'''
                <button class="btn-roll-dice"
                        @click="roll('1d20{mod_str}', entityId, 'ability_check', '{attr_label} Check')">
                    🎲 Roll
                </button>
                '''

            html.append(f'''
                <div class="attribute-card">
                    <div class="attribute-label">{attr_label}</div>
                    <div class="attribute-score">{score}</div>
                    <div class="attribute-modifier">{mod_str}</div>
                    {dice_btn}
                </div>
            ''')

        html.append('</div>')

        # Saving Throws Section
        html.append('<div class="saving-throws" style="margin-top: 1.5rem;">')
        html.append('<h4 style="margin: 0 0 0.75rem 0; font-size: 1rem; color: var(--primary-color);">Saving Throws</h4>')
        html.append('<div class="saves-grid">')

        for attr_key, attr_label in attributes:
            score = data.get(attr_key, 10)
            mod = self.calculate_modifier(score)

            # Check if proficient in this save
            is_proficient = attr_key in save_profs
            save_bonus = mod + (proficiency_bonus if is_proficient else 0)
            save_str = f"+{save_bonus}" if save_bonus >= 0 else str(save_bonus)

            prof_marker = '⭐ ' if is_proficient else ''

            # Dice button for saving throw
            dice_btn = ''
            if entity_id:
                dice_btn = f'''
                <button class="btn-roll-dice inline"
                        @click="roll('1d20{save_str}', entityId, 'saving_throw', '{attr_label} Save')">
                    🎲
                </button>
                '''

            html.append(f'''
                <div class="save-row">
                    <div class="save-name">{prof_marker}{attr_label}</div>
                    <div class="save-bonus">{save_str}</div>
                    {dice_btn}
                </div>
            ''')

        html.append('</div>')
        html.append('</div>')

        html.append('</div>')

        # Add CSS
        html.append('''
        <style>
        .saves-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }
        .save-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0.5rem;
            background: var(--background-color);
            border-radius: 4px;
        }
        .save-name {
            flex: 1;
            font-weight: 500;
            font-size: 0.9rem;
        }
        .save-bonus {
            min-width: 2rem;
            text-align: right;
            font-weight: bold;
            color: var(--primary-color);
            font-size: 0.9rem;
        }
        </style>
        ''')

        return ''.join(html)

    @staticmethod
    def calculate_modifier(score: int) -> int:
        """
        Calculate ability modifier from score.

        Formula: (score - 10) // 2

        Args:
            score: Ability score (1-30)

        Returns:
            Ability modifier (-5 to +10 for scores 1-30)

        Examples:
            calculate_modifier(10) -> 0
            calculate_modifier(16) -> +3
            calculate_modifier(8) -> -1
        """
        return (score - 10) // 2

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """Validate attribute scores are within reasonable bounds."""
        for attr_name in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
            score = data.get(attr_name)
            if score is not None and (score < 1 or score > 30):
                raise ValueError(f"{attr_name} must be between 1 and 30, got {score}")
        return True
