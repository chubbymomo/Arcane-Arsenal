"""
Experience Component for Generic Fantasy Module.

Provides experience point tracking and level progression.
"""

from typing import Dict, Any
from ..base import ComponentTypeDefinition


class ExperienceComponent(ComponentTypeDefinition):
    """
    Experience points and leveling component.

    Tracks current XP and provides level progression information.
    Uses a standard fantasy RPG XP curve.
    """

    type = "Experience"
    description = "Experience points and level progression"
    schema_version = "1.0.0"
    module = "generic_fantasy"

    # Standard XP thresholds for levels 1-20
    XP_THRESHOLDS = [
        0,      # Level 1
        300,    # Level 2
        900,    # Level 3
        2700,   # Level 4
        6500,   # Level 5
        14000,  # Level 6
        23000,  # Level 7
        34000,  # Level 8
        48000,  # Level 9
        64000,  # Level 10
        85000,  # Level 11
        100000, # Level 12
        120000, # Level 13
        140000, # Level 14
        165000, # Level 15
        195000, # Level 16
        225000, # Level 17
        265000, # Level 18
        305000, # Level 19
        355000  # Level 20
    ]

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for experience."""
        return {
            "type": "object",
            "properties": {
                "current_xp": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Current experience points"
                },
                "total_xp": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Total XP earned (including spent XP if applicable)"
                }
            },
            "required": ["current_xp"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Return UI metadata for experience."""
        return {
            "current_xp": {
                "label": "Current XP",
                "widget": "number",
                "order": 0,
                "help_text": "Current experience points",
                "min": 0,
                "step": 1
            },
            "total_xp": {
                "label": "Total XP Earned",
                "widget": "number",
                "order": 1,
                "help_text": "Total experience points earned over character's lifetime",
                "min": 0,
                "step": 1
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        """Experience appears in the INFO category."""
        return {
            "visible": True,
            "category": "info",
            "priority": 2,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer with XP bar and level progression."""
        from markupsafe import escape

        current_xp = data.get('current_xp', 0)
        total_xp = data.get('total_xp', current_xp)

        # Calculate level from XP
        level = self.calculate_level(current_xp)
        next_level = min(level + 1, 20)

        # Get XP needed for next level
        xp_for_current_level = self.XP_THRESHOLDS[level - 1] if level > 1 else 0
        xp_for_next_level = self.XP_THRESHOLDS[next_level - 1] if next_level <= 20 else self.XP_THRESHOLDS[-1]

        # Calculate progress to next level
        xp_into_level = current_xp - xp_for_current_level
        xp_needed_for_level = xp_for_next_level - xp_for_current_level

        if xp_needed_for_level > 0:
            progress_percent = int((xp_into_level / xp_needed_for_level) * 100)
        else:
            progress_percent = 100  # Max level

        html = ['<div class="experience-display">']
        html.append('<dl class="component-data">')
        html.append(f'<dt>Level</dt><dd>{level}</dd>')
        html.append(f'<dt>Current XP</dt><dd>{current_xp:,}</dd>')

        if level < 20:
            html.append(f'<dt>XP to Next Level</dt><dd>{xp_for_next_level - current_xp:,}</dd>')

        if total_xp > current_xp:
            html.append(f'<dt>Total XP Earned</dt><dd>{total_xp:,}</dd>')

        html.append('</dl>')

        # XP Progress bar
        if level < 20:
            html.append(f'''
                <div class="xp-progress" style="margin-top: 1rem;">
                    <div class="xp-label" style="margin-bottom: 0.25rem; font-size: 0.9rem; color: var(--text-muted);">
                        Level {level} → Level {next_level}
                    </div>
                    <div class="hp-bar-container" style="height: 24px; margin-bottom: 0.25rem;">
                        <div class="hp-bar" style="width: {progress_percent}%; background: linear-gradient(90deg, #6c5ce7, #a29bfe);"></div>
                        <div class="hp-text" style="font-size: 0.9rem;">
                            {xp_into_level:,} / {xp_needed_for_level:,} XP ({progress_percent}%)
                        </div>
                    </div>
                </div>
            ''')
        else:
            html.append('<p style="margin-top: 1rem; font-weight: bold; color: var(--primary-color);">⭐ Maximum Level Reached!</p>')

        html.append('</div>')
        return ''.join(html)

    @staticmethod
    def calculate_level(xp: int) -> int:
        """
        Calculate character level from XP.

        Args:
            xp: Current experience points

        Returns:
            Character level (1-20)

        Examples:
            calculate_level(0) -> 1
            calculate_level(300) -> 2
            calculate_level(1000) -> 3
        """
        thresholds = ExperienceComponent.XP_THRESHOLDS
        for level in range(len(thresholds) - 1, -1, -1):
            if xp >= thresholds[level]:
                return level + 1
        return 1

    @staticmethod
    def xp_for_level(level: int) -> int:
        """
        Get XP threshold for a given level.

        Args:
            level: Target level (1-20)

        Returns:
            XP required to reach that level

        Examples:
            xp_for_level(1) -> 0
            xp_for_level(5) -> 6500
            xp_for_level(20) -> 355000
        """
        if level < 1:
            return 0
        if level > 20:
            level = 20
        return ExperienceComponent.XP_THRESHOLDS[level - 1]
