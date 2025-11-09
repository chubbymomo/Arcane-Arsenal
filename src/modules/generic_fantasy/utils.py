"""
Utility functions for Generic Fantasy Module.

Provides calculation helpers for:
- Proficiency bonus by level
- Spell slot progression
- Ability modifiers
"""

from typing import Dict


def calculate_proficiency_bonus(level: int) -> int:
    """
    Calculate proficiency bonus from character level.

    Standard D&D/fantasy progression: +2 at level 1, increases by 1 every 4 levels.

    Args:
        level: Character level (1-20)

    Returns:
        Proficiency bonus (+2 to +6)

    Examples:
        calculate_proficiency_bonus(1) -> 2
        calculate_proficiency_bonus(5) -> 3
        calculate_proficiency_bonus(9) -> 4
        calculate_proficiency_bonus(17) -> 6
    """
    if level < 1:
        level = 1
    if level > 20:
        level = 20

    return 2 + ((level - 1) // 4)


def calculate_ability_modifier(score: int) -> int:
    """
    Calculate ability modifier from ability score.

    Formula: (score - 10) // 2

    Args:
        score: Ability score (1-30)

    Returns:
        Ability modifier (-5 to +10)

    Examples:
        calculate_ability_modifier(10) -> 0
        calculate_ability_modifier(16) -> +3
        calculate_ability_modifier(8) -> -1
    """
    return (score - 10) // 2


# Spell slot progression tables

FULL_CASTER_SLOTS = {
    1: {"1": {"current": 2, "max": 2}},
    2: {"1": {"current": 3, "max": 3}},
    3: {"1": {"current": 4, "max": 4}, "2": {"current": 2, "max": 2}},
    4: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}},
    5: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 2, "max": 2}},
    6: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}},
    7: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 1, "max": 1}},
    8: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 2, "max": 2}},
    9: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 1, "max": 1}},
    10: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}},
    11: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}, "6": {"current": 1, "max": 1}},
    12: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}, "6": {"current": 1, "max": 1}},
    13: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}, "6": {"current": 1, "max": 1}, "7": {"current": 1, "max": 1}},
    14: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}, "6": {"current": 1, "max": 1}, "7": {"current": 1, "max": 1}},
    15: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}, "6": {"current": 1, "max": 1}, "7": {"current": 1, "max": 1}, "8": {"current": 1, "max": 1}},
    16: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}, "6": {"current": 1, "max": 1}, "7": {"current": 1, "max": 1}, "8": {"current": 1, "max": 1}},
    17: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}, "6": {"current": 1, "max": 1}, "7": {"current": 1, "max": 1}, "8": {"current": 1, "max": 1}, "9": {"current": 1, "max": 1}},
    18: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 3, "max": 3}, "6": {"current": 1, "max": 1}, "7": {"current": 1, "max": 1}, "8": {"current": 1, "max": 1}, "9": {"current": 1, "max": 1}},
    19: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 3, "max": 3}, "6": {"current": 2, "max": 2}, "7": {"current": 1, "max": 1}, "8": {"current": 1, "max": 1}, "9": {"current": 1, "max": 1}},
    20: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 3, "max": 3}, "6": {"current": 2, "max": 2}, "7": {"current": 2, "max": 2}, "8": {"current": 1, "max": 1}, "9": {"current": 1, "max": 1}},
}

HALF_CASTER_SLOTS = {
    1: {},  # No spells at level 1
    2: {"1": {"current": 2, "max": 2}},
    3: {"1": {"current": 3, "max": 3}},
    4: {"1": {"current": 3, "max": 3}},
    5: {"1": {"current": 4, "max": 4}, "2": {"current": 2, "max": 2}},
    6: {"1": {"current": 4, "max": 4}, "2": {"current": 2, "max": 2}},
    7: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}},
    8: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}},
    9: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 2, "max": 2}},
    10: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 2, "max": 2}},
    11: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}},
    12: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}},
    13: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 1, "max": 1}},
    14: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 1, "max": 1}},
    15: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 2, "max": 2}},
    16: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 2, "max": 2}},
    17: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 1, "max": 1}},
    18: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 1, "max": 1}},
    19: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}},
    20: {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 3, "max": 3}, "4": {"current": 3, "max": 3}, "5": {"current": 2, "max": 2}},
}


def get_spell_slots_for_level(level: int, progression: str) -> Dict[str, Dict[str, int]]:
    """
    Get spell slots for a character's level and spell progression type.

    Args:
        level: Character level (1-20)
        progression: Spell progression type ('full', 'half', or 'none')

    Returns:
        Dictionary of spell slots by level with current and max values

    Examples:
        get_spell_slots_for_level(3, 'full') ->
            {"1": {"current": 4, "max": 4}, "2": {"current": 2, "max": 2}}

        get_spell_slots_for_level(5, 'half') ->
            {"1": {"current": 4, "max": 4}, "2": {"current": 2, "max": 2}}

        get_spell_slots_for_level(10, 'none') -> {}
    """
    if level < 1:
        level = 1
    if level > 20:
        level = 20

    if progression == 'full':
        return FULL_CASTER_SLOTS.get(level, {}).copy()
    elif progression == 'half':
        return HALF_CASTER_SLOTS.get(level, {}).copy()
    else:
        return {}


def should_auto_add_magic(class_name: str, class_metadata: Dict) -> bool:
    """
    Determine if a character with this class should have Magic component auto-added.

    Args:
        class_name: Name of the class
        class_metadata: Metadata dictionary from class registry

    Returns:
        True if class is a spellcaster

    Examples:
        should_auto_add_magic('wizard', {'spellcaster': True}) -> True
        should_auto_add_magic('fighter', {'spellcaster': False}) -> False
    """
    return class_metadata.get('spellcaster', False)


__all__ = [
    'calculate_proficiency_bonus',
    'calculate_ability_modifier',
    'get_spell_slots_for_level',
    'should_auto_add_magic',
    'FULL_CASTER_SLOTS',
    'HALF_CASTER_SLOTS'
]
