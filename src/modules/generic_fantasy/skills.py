"""
Skills Component for Generic Fantasy Module.

Provides skill proficiency tracking for fantasy characters.
"""

from typing import Dict, Any, List
from ..base import ComponentTypeDefinition


class SkillsComponent(ComponentTypeDefinition):
    """
    Skill proficiency tracking component.

    Tracks which skills a character is proficient in and their proficiency bonus.
    Skills are validated against the skill_types registry.
    """

    type = "Skills"
    description = "Skill proficiencies and bonuses"
    schema_version = "1.0.0"
    module = "generic_fantasy"

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for skills."""
        return {
            "type": "object",
            "properties": {
                "proficient_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of skills the character is proficient in",
                    "default": []
                },
                "proficiency_bonus": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 2,
                    "description": "Proficiency bonus added to proficient skills"
                },
                "expertise_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills with expertise (double proficiency)",
                    "default": []
                }
            },
            "required": ["proficient_skills", "proficiency_bonus"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Return UI metadata for skills."""
        return {
            "proficiency_bonus": {
                "label": "Proficiency Bonus",
                "widget": "number",
                "order": 0,
                "help_text": "Bonus added to proficient skills and attacks",
                "min": 0,
                "max": 10,
                "step": 1
            },
            "proficient_skills": {
                "label": "Proficient Skills",
                "widget": "multi-select",
                "registry": "skill_types",
                "order": 1,
                "help_text": "Skills this character is proficient in"
            },
            "expertise_skills": {
                "label": "Expertise Skills",
                "widget": "multi-select",
                "registry": "skill_types",
                "order": 2,
                "help_text": "Skills with expertise (double proficiency)"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Skills appear in the SKILLS category."""
        return {
            "visible": True,
            "category": "skills",
            "priority": 1,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer for skills with roll buttons."""
        from markupsafe import escape

        proficient_skills = data.get('proficient_skills', [])
        expertise_skills = data.get('expertise_skills', [])
        proficiency_bonus = data.get('proficiency_bonus', 2)

        # Get all skills from registry
        all_skills = []
        if engine:
            try:
                skills_registry = engine.create_registry('skill_types', self.module)
                all_skills = skills_registry.get_all()
            except Exception:
                pass

        # If no registry or entity, fall back to simple display
        if not all_skills or not entity_id:
            html = ['<div class="skills-display">']
            html.append(f'<p><strong>Proficiency Bonus:</strong> +{proficiency_bonus}</p>')
            if proficient_skills:
                html.append('<p><strong>Proficient:</strong> ' + ', '.join(escape(s) for s in proficient_skills) + '</p>')
            if expertise_skills:
                html.append('<p><strong>Expertise:</strong> ' + ', '.join(escape(s) for s in expertise_skills) + '</p>')
            html.append('</div>')
            return ''.join(html)

        # Get attributes for calculating skill bonuses
        attributes_data = None
        if engine and entity_id:
            attributes = engine.get_component(entity_id, 'Attributes')
            if attributes:
                attributes_data = attributes.data

        html = ['<div class="skills-grid">']

        for skill in all_skills:
            skill_key = skill['key']
            skill_desc = skill['description']
            skill_meta = skill.get('metadata', {})
            ability = skill_meta.get('ability', 'strength')

            # Calculate skill bonus
            ability_mod = 0
            if attributes_data:
                ability_score = attributes_data.get(ability, 10)
                ability_mod = (ability_score - 10) // 2

            # Check proficiency
            is_proficient = skill_key in proficient_skills
            has_expertise = skill_key in expertise_skills

            if has_expertise:
                skill_bonus = ability_mod + (proficiency_bonus * 2)
                prof_marker = "⭐⭐"
            elif is_proficient:
                skill_bonus = ability_mod + proficiency_bonus
                prof_marker = "⭐"
            else:
                skill_bonus = ability_mod
                prof_marker = ""

            bonus_str = f"+{skill_bonus}" if skill_bonus >= 0 else str(skill_bonus)

            # Extract skill name from description (before the dash)
            skill_name = skill_desc.split(' - ')[0] if ' - ' in skill_desc else skill_key.replace('_', ' ').title()

            html.append(f'''
                <div class="skill-row">
                    <div class="skill-name">{prof_marker} {escape(skill_name)}</div>
                    <div class="skill-bonus">{bonus_str}</div>
                    <button class="btn-roll-dice inline"
                            @click="roll('1d20{bonus_str}', entityId, 'skill_check', '{escape(skill_name)} Check')">
                        🎲
                    </button>
                </div>
            ''')

        html.append('</div>')

        # Add CSS for skills grid
        html.append('''
        <style>
        .skills-grid {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        .skill-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0.5rem;
            background: var(--background-color);
            border-radius: 4px;
        }
        .skill-name {
            flex: 1;
            font-weight: 500;
        }
        .skill-bonus {
            min-width: 2.5rem;
            text-align: right;
            font-weight: bold;
            color: var(--primary-color);
        }
        </style>
        ''')

        return ''.join(html)

    def validate_with_engine(self, data: Dict[str, Any], engine) -> bool:
        """
        Validate skill names against skill_types registry.

        Args:
            data: Component data to validate
            engine: StateEngine instance for querying registries

        Returns:
            True if valid

        Raises:
            ValueError: If any skill not in skill_types registry
        """
        proficient_skills = data.get('proficient_skills', [])
        expertise_skills = data.get('expertise_skills', [])

        # Get skills registry
        skills_registry = engine.create_registry('skill_types', self.module)
        valid_skills = set(skills_registry.get_keys())

        # Validate proficient skills
        for skill in proficient_skills:
            if skill not in valid_skills:
                raise ValueError(
                    f"Invalid skill '{skill}'. "
                    f"Valid skills: {', '.join(sorted(valid_skills))}"
                )

        # Validate expertise skills
        for skill in expertise_skills:
            if skill not in valid_skills:
                raise ValueError(
                    f"Invalid expertise skill '{skill}'. "
                    f"Valid skills: {', '.join(sorted(valid_skills))}"
                )

            # Expertise requires proficiency
            if skill not in proficient_skills:
                raise ValueError(
                    f"Cannot have expertise in '{skill}' without proficiency. "
                    f"Add to proficient_skills first."
                )

        return True
