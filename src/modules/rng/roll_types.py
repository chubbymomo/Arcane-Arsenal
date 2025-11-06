"""
Core roll type definitions for RNG module.

These define the valid roll_type values that can be used in roll requests.
Other modules can register additional roll types.
"""

from src.modules.base import RollTypeDefinition


def core_roll_types():
    """Return core roll types provided by RNG module."""
    return [
        RollTypeDefinition(
            type='attack',
            description='Attack roll to determine if an attack hits',
            module='rng',
            category='combat'
        ),
        RollTypeDefinition(
            type='damage',
            description='Damage roll to determine how much damage is dealt',
            module='rng',
            category='combat'
        ),
        RollTypeDefinition(
            type='saving_throw',
            description='Saving throw to resist effects',
            module='rng',
            category='saving_throw'
        ),
        RollTypeDefinition(
            type='skill_check',
            description='Skill check to perform an action',
            module='rng',
            category='skill'
        ),
        RollTypeDefinition(
            type='initiative',
            description='Initiative roll to determine turn order',
            module='rng',
            category='combat'
        ),
        RollTypeDefinition(
            type='ability_check',
            description='Ability check using raw ability score',
            module='rng',
            category='ability'
        ),
    ]
