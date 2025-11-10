"""
CharacterDetails Component for Generic Fantasy Module.

Provides character identity information including race, class, background,
alignment, and level.
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class CharacterDetailsComponent(ComponentTypeDefinition):
    """
    Character identity and background information.

    Tracks race, class, background, alignment, and level for fantasy characters.
    These details provide context for roleplay and mechanical bonuses.
    """

    type = "CharacterDetails"
    description = "Character race, class, background, alignment, and level"
    schema_version = "1.0.0"
    module = "generic_fantasy"

    def get_schema(self) -> Dict[str, Any]:
        """
        Return JSON Schema for character details.

        Note: race is always required. character_class and level are required
        for mechanically-defined characters (players, combat NPCs) but optional
        for simple NPCs who only need race for description.
        """
        return {
            "type": "object",
            "properties": {
                "race": {
                    "type": "string",
                    "description": "Character's race (e.g., human, elf, dwarf)"
                },
                "character_class": {
                    "type": "string",
                    "description": "Character's class (e.g., fighter, wizard, rogue). Optional for simple NPCs."
                },
                "background": {
                    "type": "string",
                    "description": "Character's background (e.g., soldier, sage, criminal)"
                },
                "alignment": {
                    "type": "string",
                    "description": "Character's moral alignment"
                },
                "level": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 1,
                    "description": "Character level. Defaults to 1 if not specified."
                }
            },
            "required": ["race"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Return UI metadata for character details."""
        return {
            "race": {
                "label": "Race",
                "widget": "select",
                "registry": "races",
                "order": 0,
                "help_text": "Character's race or ancestry"
            },
            "character_class": {
                "label": "Class",
                "widget": "select",
                "registry": "classes",
                "order": 1,
                "help_text": "Character's profession or class"
            },
            "background": {
                "label": "Background",
                "widget": "text",
                "order": 2,
                "help_text": "Character's background or origin story",
                "placeholder": "e.g., Soldier, Sage, Noble"
            },
            "alignment": {
                "label": "Alignment",
                "widget": "select",
                "registry": "alignments",
                "order": 3,
                "help_text": "Character's moral and ethical outlook"
            },
            "level": {
                "label": "Level",
                "widget": "number",
                "order": 4,
                "help_text": "Character's experience level",
                "min": 1,
                "max": 20,
                "step": 1
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """CharacterDetails appear in the INFO category."""
        return {
            "visible": True,
            "category": "info",
            "priority": 1,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer for character details."""
        from markupsafe import escape

        race = data.get('race', 'Unknown')
        char_class = data.get('character_class', 'Unknown')
        background = data.get('background', '')
        alignment = data.get('alignment', '')
        level = data.get('level', 1)

        html = ['<div class="character-details-display">']
        html.append('<dl class="component-data">')
        html.append(f'<dt>Level</dt><dd>{escape(str(level))}</dd>')
        html.append(f'<dt>Race</dt><dd>{escape(race).title()}</dd>')
        html.append(f'<dt>Class</dt><dd>{escape(char_class).title()}</dd>')

        if background:
            html.append(f'<dt>Background</dt><dd>{escape(background)}</dd>')

        if alignment:
            # Format alignment nicely
            alignment_formatted = alignment.replace('_', ' ').title()
            html.append(f'<dt>Alignment</dt><dd>{escape(alignment_formatted)}</dd>')

        html.append('</dl>')
        html.append('</div>')
        return ''.join(html)

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """
        Validate race, class, and alignment against registries.

        Args:
            data: Component data to validate
            engine: StateEngine instance for querying registries

        Returns:
            True if valid

        Raises:
            ValueError: If race, class, or alignment not in respective registries
        """
        # Validate race
        race = data.get('race')
        if race:
            races_registry = engine.create_registry('races', self.module)
            try:
                races_registry.validate(race, 'race')
            except ValueError as e:
                raise ValueError(
                    f"Invalid race '{race}'. "
                    f"Valid races: {', '.join(races_registry.get_keys())}"
                )

        # Validate character_class (optional - only if provided)
        char_class = data.get('character_class')
        if char_class:
            classes_registry = engine.create_registry('classes', self.module)
            try:
                classes_registry.validate(char_class, 'character_class')
            except ValueError as e:
                raise ValueError(
                    f"Invalid class '{char_class}'. "
                    f"Valid classes: {', '.join(classes_registry.get_keys())}"
                )
        # Note: character_class is now optional, so NPCs can have just race without class

        # Validate alignment (optional field)
        alignment = data.get('alignment')
        if alignment:
            alignments_registry = engine.create_registry('alignments', self.module)
            try:
                alignments_registry.validate(alignment, 'alignment')
            except ValueError as e:
                raise ValueError(
                    f"Invalid alignment '{alignment}'. "
                    f"Valid alignments: {', '.join(alignments_registry.get_keys())}"
                )

        # Validate level
        level = data.get('level', 1)
        if level < 1 or level > 20:
            raise ValueError(f"Level must be between 1 and 20, got {level}")

        return True
