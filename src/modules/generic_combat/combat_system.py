"""
Combat System for Arcane Arsenal.

Provides combat encounter management, initiative tracking, attack resolution,
and condition/status effect handling. This bridges the gap between basic combat
components (Health, Armor, Weapon) and the AI DM's combat tools.

Key Features:
- Combat encounter state management
- Initiative tracking and turn order
- Attack resolution (roll → AC check → damage)
- Condition/status effect application
- Integration with character attributes and skills
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from ..base import ComponentTypeDefinition

logger = logging.getLogger(__name__)


class CombatEncounterComponent(ComponentTypeDefinition):
    """
    Component that tracks an active combat encounter.

    Attached to a special 'combat' entity that exists only during combat.
    Tracks participants, turn order, and combat state.
    """

    type = "CombatEncounter"
    description = "Tracks active combat encounter state"
    schema_version = "1.0.0"
    module = "generic_combat"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "participants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entity IDs of all combatants"
                },
                "turn_order": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entity IDs in initiative order"
                },
                "current_turn_index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Index of current turn in turn_order"
                },
                "round_number": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Current combat round"
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether combat is ongoing"
                }
            },
            "required": ["participants", "turn_order", "current_turn_index", "round_number", "is_active"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "round_number": {
                "label": "Round",
                "widget": "number",
                "order": 0,
                "help_text": "Current combat round"
            },
            "is_active": {
                "label": "Combat Active",
                "widget": "checkbox",
                "order": 1,
                "help_text": "Whether combat is ongoing"
            }
        }


class InitiativeComponent(ComponentTypeDefinition):
    """
    Component that tracks initiative for a combatant.

    Attached to entities participating in combat.
    """

    type = "Initiative"
    description = "Initiative order and combat actions"
    schema_version = "1.0.0"
    module = "generic_combat"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "initiative_roll": {
                    "type": "integer",
                    "description": "Initiative roll result (d20 + DEX modifier)"
                },
                "dexterity_modifier": {
                    "type": "integer",
                    "description": "DEX modifier used for tiebreaking"
                },
                "has_acted": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether this combatant has acted this round"
                },
                "actions_remaining": {
                    "type": "integer",
                    "default": 1,
                    "description": "Number of actions remaining this turn"
                },
                "bonus_actions_remaining": {
                    "type": "integer",
                    "default": 1,
                    "description": "Number of bonus actions remaining this turn"
                },
                "reaction_available": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether reaction is available"
                }
            },
            "required": ["initiative_roll", "dexterity_modifier"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "initiative_roll": {
                "label": "Initiative",
                "widget": "number",
                "order": 0,
                "help_text": "Initiative roll result"
            },
            "actions_remaining": {
                "label": "Actions",
                "widget": "number",
                "order": 1,
                "help_text": "Actions left this turn"
            }
        }


class CombatConditionComponent(ComponentTypeDefinition):
    """
    Component that tracks status effects and conditions.

    Examples: blinded, stunned, poisoned, blessed, hasted, etc.
    Multiple conditions can be applied by adding multiple instances
    or using an array structure.
    """

    type = "CombatCondition"
    description = "Status effects and combat conditions"
    schema_version = "1.0.0"
    module = "generic_combat"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "conditions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Condition name"
                            },
                            "description": {
                                "type": "string",
                                "description": "What the condition does"
                            },
                            "duration_type": {
                                "type": "string",
                                "enum": ["rounds", "minutes", "hours", "permanent", "until_save", "concentration"],
                                "description": "How long the condition lasts"
                            },
                            "duration_remaining": {
                                "type": "integer",
                                "minimum": 0,
                                "description": "Rounds/minutes/hours remaining"
                            },
                            "save_dc": {
                                "type": "integer",
                                "description": "DC for saving throw to end effect (if applicable)"
                            },
                            "save_ability": {
                                "type": "string",
                                "description": "Ability for save (strength, dexterity, etc.)"
                            },
                            "source_entity_id": {
                                "type": "string",
                                "description": "Entity that applied this condition"
                            }
                        },
                        "required": ["name", "description", "duration_type"]
                    },
                    "description": "List of active conditions"
                }
            },
            "required": ["conditions"]
        }

    def get_ui_metadata(self) -> Dict[str, Dict[str, Any]]:
        return {
            "conditions": {
                "label": "Conditions",
                "widget": "custom",
                "order": 0,
                "help_text": "Active status effects"
            }
        }

    def get_character_sheet_config(self) -> Dict[str, Any]:
        return {
            "visible": True,
            "category": "combat",
            "priority": 5,
            "display_mode": "full"
        }

    def get_character_sheet_renderer(self, data: Dict[str, Any], engine=None, entity_id=None) -> str:
        """Custom renderer for conditions with visual badges."""
        from markupsafe import escape

        conditions = data.get('conditions', [])

        if not conditions:
            return '<div class="no-conditions"><em>No active conditions</em></div>'

        html_parts = ['<div class="combat-conditions">']

        for condition in conditions:
            name = escape(condition.get('name', 'Unknown'))
            description = escape(condition.get('description', ''))
            duration_type = condition.get('duration_type', 'rounds')
            duration = condition.get('duration_remaining', 0)

            # Determine badge color based on condition type
            if any(bad in name.lower() for bad in ['poison', 'stun', 'blind', 'paralyze', 'frighten']):
                badge_class = 'badge-danger'
            elif any(good in name.lower() for good in ['bless', 'haste', 'inspire', 'aid']):
                badge_class = 'badge-success'
            else:
                badge_class = 'badge-warning'

            duration_text = ''
            if duration_type == 'rounds' and duration > 0:
                duration_text = f' ({duration} rounds)'
            elif duration_type == 'concentration':
                duration_text = ' (Concentration)'
            elif duration_type == 'permanent':
                duration_text = ' (Permanent)'

            html_parts.append(f'''
                <div class="condition-badge {badge_class}" style="margin: 0.25rem; padding: 0.5rem; border-radius: 4px; background: rgba(255,255,255,0.1);">
                    <strong>{name}</strong>{duration_text}
                    <div style="font-size: 0.9em; opacity: 0.8;">{description}</div>
                </div>
            ''')

        html_parts.append('</div>')
        return ''.join(html_parts)


# ============================================================================
# Combat System Helper Functions
# ============================================================================

def calculate_ability_modifier(ability_score: int) -> int:
    """Calculate ability modifier from ability score."""
    return (ability_score - 10) // 2


def get_attack_modifier(engine, attacker_id: str, attack_type: str = 'melee') -> int:
    """
    Calculate total attack bonus for an entity.

    Args:
        engine: StateEngine instance
        attacker_id: Entity making the attack
        attack_type: 'melee', 'ranged', or 'spell'

    Returns:
        Total attack modifier
    """
    modifier = 0

    # Get attributes
    attributes = engine.get_component(attacker_id, 'Attributes')
    if attributes:
        attrs_data = attributes.data

        # Determine which ability to use
        if attack_type == 'melee':
            # Use STR for melee (could be DEX for finesse weapons)
            ability_score = attrs_data.get('strength', 10)
        elif attack_type == 'ranged':
            # Use DEX for ranged
            ability_score = attrs_data.get('dexterity', 10)
        elif attack_type == 'spell':
            # Get spellcasting ability from Magic component
            magic = engine.get_component(attacker_id, 'Magic')
            if magic:
                spell_ability = magic.data.get('spellcasting_ability', 'intelligence')
                ability_score = attrs_data.get(spell_ability, 10)
            else:
                ability_score = attrs_data.get('intelligence', 10)
        else:
            ability_score = 10

        modifier += calculate_ability_modifier(ability_score)

    # Add proficiency bonus
    char_details = engine.get_component(attacker_id, 'CharacterDetails')
    if char_details:
        level = char_details.data.get('level', 1)
        proficiency = calculate_proficiency_bonus(level)
        modifier += proficiency

    return modifier


def get_spell_attack_modifier(engine, caster_id: str) -> int:
    """Get spell attack bonus for a caster."""
    magic = engine.get_component(caster_id, 'Magic')
    if not magic:
        return 0

    return magic.data.get('spell_attack_bonus', 0)


def get_armor_class(engine, entity_id: str) -> int:
    """
    Get the armor class for an entity.

    Args:
        engine: StateEngine instance
        entity_id: Entity to check

    Returns:
        Armor class value
    """
    armor = engine.get_component(entity_id, 'Armor')
    if armor:
        return armor.data.get('armor_class', 10)

    # If no armor component, calculate from DEX
    attributes = engine.get_component(entity_id, 'Attributes')
    if attributes:
        dex = attributes.data.get('dexterity', 10)
        return 10 + calculate_ability_modifier(dex)

    return 10  # Default AC


def calculate_proficiency_bonus(level: int) -> int:
    """Calculate proficiency bonus from character level."""
    return 2 + (level - 1) // 4


def resolve_attack(
    engine,
    attacker_id: str,
    target_id: str,
    attack_type: str = 'melee',
    damage_dice: str = None,
    damage_type: str = 'bludgeoning',
    advantage: bool = False,
    disadvantage: bool = False
) -> Dict[str, Any]:
    """
    Resolve a complete attack sequence.

    Args:
        engine: StateEngine instance
        attacker_id: Entity making the attack
        target_id: Entity being attacked
        attack_type: 'melee', 'ranged', or 'spell'
        damage_dice: Damage dice notation (e.g., '1d8+3'). If None, uses equipped weapon.
        damage_type: Type of damage
        advantage: Whether to roll with advantage
        disadvantage: Whether to roll with disadvantage

    Returns:
        Dict with attack results including hit/miss, damage dealt, etc.
    """
    from src.modules.rng.dice_roller import DiceRoller

    roller = DiceRoller(engine)

    # Step 1: Roll attack
    attack_mod = get_attack_modifier(engine, attacker_id, attack_type)
    attack_notation = f"1d20+{attack_mod}" if attack_mod >= 0 else f"1d20{attack_mod}"

    attack_roll_result = roller.roll(
        attacker_id,
        attack_notation,
        roll_type='attack',
        advantage=advantage,
        disadvantage=disadvantage
    )

    if not attack_roll_result.success:
        return {
            "success": False,
            "message": f"Failed to roll attack: {attack_roll_result.error}"
        }

    attack_total = attack_roll_result.data['total']
    is_crit = attack_roll_result.data.get('critical_success', False)
    is_fumble = attack_roll_result.data.get('critical_failure', False)

    # Step 2: Check against AC
    target_ac = get_armor_class(engine, target_id)
    hit = attack_total >= target_ac

    # Step 3: Roll damage if hit
    damage_dealt = 0
    damage_roll_result = None

    if hit or is_crit:
        # Get damage dice
        if not damage_dice:
            # Try to get from equipped weapon
            weapon = engine.get_component(attacker_id, 'Weapon')
            if weapon:
                damage_dice = weapon.data.get('damage_dice', '1d4')
            else:
                damage_dice = '1d4'  # Default unarmed

        # Critical hit: double damage dice
        if is_crit:
            # Parse the dice and double them (e.g., '2d6+3' -> '4d6+3')
            from src.modules.rng.dice_parser import DiceParser
            parser = DiceParser()
            parsed = parser.parse(damage_dice)

            # Double all dice (but not modifiers)
            doubled_dice = []
            for part in parsed:
                if part['type'] == 'dice':
                    doubled_dice.append(f"{part['count'] * 2}d{part['sides']}")
                elif part['type'] == 'modifier':
                    doubled_dice.append(f"+{part['value']}" if part['value'] >= 0 else str(part['value']))

            damage_dice = ''.join(doubled_dice)

        # Roll damage
        damage_roll_result = roller.roll(
            attacker_id,
            damage_dice,
            roll_type='damage'
        )

        if damage_roll_result.success:
            damage_dealt = max(0, damage_roll_result.data['total'])

            # Apply damage to target
            apply_damage(engine, target_id, damage_dealt, damage_type)

    # Step 4: Build result
    result = {
        "success": True,
        "hit": hit,
        "critical": is_crit,
        "fumble": is_fumble,
        "attack_roll": attack_total,
        "target_ac": target_ac,
        "damage_dealt": damage_dealt,
        "damage_type": damage_type,
        "attacker_id": attacker_id,
        "target_id": target_id,
        "message": ""
    }

    # Create message
    if is_fumble:
        result["message"] = f"Critical miss! (rolled {attack_roll_result.data.get('raw_rolls', [1])[0]})"
    elif is_crit:
        result["message"] = f"Critical hit! Rolled {attack_total} vs AC {target_ac}, dealt {damage_dealt} {damage_type} damage!"
    elif hit:
        result["message"] = f"Hit! Rolled {attack_total} vs AC {target_ac}, dealt {damage_dealt} {damage_type} damage."
    else:
        result["message"] = f"Miss. Rolled {attack_total} vs AC {target_ac}."

    return result


def apply_damage(
    engine,
    target_id: str,
    damage_amount: int,
    damage_type: str = 'untyped'
) -> Dict[str, Any]:
    """
    Apply damage to an entity's health.

    Handles temporary HP absorption and HP reduction.

    Args:
        engine: StateEngine instance
        target_id: Entity taking damage
        damage_amount: Amount of damage to deal
        damage_type: Type of damage

    Returns:
        Dict with damage results
    """
    health = engine.get_component(target_id, 'Health')
    if not health:
        return {
            "success": False,
            "message": "Target has no Health component"
        }

    health_data = health.data.copy()
    current_hp = health_data.get('current_hp', 0)
    temp_hp = health_data.get('temp_hp', 0)
    max_hp = health_data.get('max_hp', 1)

    # Temp HP absorbs damage first
    if temp_hp > 0:
        if damage_amount <= temp_hp:
            health_data['temp_hp'] = temp_hp - damage_amount
            damage_amount = 0
        else:
            damage_amount -= temp_hp
            health_data['temp_hp'] = 0

    # Apply remaining damage to current HP
    health_data['current_hp'] = max(0, current_hp - damage_amount)

    # Update health component
    engine.update_component(target_id, 'Health', health_data)

    is_dead = health_data['current_hp'] <= 0

    return {
        "success": True,
        "damage_dealt": damage_amount,
        "damage_type": damage_type,
        "new_hp": health_data['current_hp'],
        "max_hp": max_hp,
        "temp_hp_absorbed": temp_hp - health_data['temp_hp'],
        "is_dead": is_dead
    }


def apply_condition(
    engine,
    target_id: str,
    condition_name: str,
    condition_description: str,
    duration_type: str = 'rounds',
    duration_remaining: int = 1,
    save_dc: Optional[int] = None,
    save_ability: Optional[str] = None,
    source_entity_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Apply a combat condition/status effect to an entity.

    Args:
        engine: StateEngine instance
        target_id: Entity to apply condition to
        condition_name: Name of condition
        condition_description: What the condition does
        duration_type: How duration is measured
        duration_remaining: How long it lasts
        save_dc: DC for saving throw to end
        save_ability: Ability for save
        source_entity_id: Who applied the condition

    Returns:
        Dict with result
    """
    # Get or create CombatCondition component
    condition_comp = engine.get_component(target_id, 'CombatCondition')

    if condition_comp:
        conditions = condition_comp.data.get('conditions', [])
    else:
        conditions = []

    # Add new condition
    new_condition = {
        "name": condition_name,
        "description": condition_description,
        "duration_type": duration_type,
        "duration_remaining": duration_remaining
    }

    if save_dc is not None:
        new_condition["save_dc"] = save_dc
    if save_ability is not None:
        new_condition["save_ability"] = save_ability
    if source_entity_id is not None:
        new_condition["source_entity_id"] = source_entity_id

    conditions.append(new_condition)

    # Update or add component
    if condition_comp:
        engine.update_component(target_id, 'CombatCondition', {'conditions': conditions})
    else:
        engine.add_component(target_id, 'CombatCondition', {'conditions': conditions})

    return {
        "success": True,
        "message": f"Applied {condition_name} to target",
        "condition": new_condition
    }


def update_condition_durations(engine, entity_id: str, end_of_turn: bool = True) -> List[str]:
    """
    Update condition durations and remove expired conditions.

    Args:
        engine: StateEngine instance
        entity_id: Entity whose conditions to update
        end_of_turn: Whether this is end of turn (vs start of turn)

    Returns:
        List of expired condition names
    """
    condition_comp = engine.get_component(entity_id, 'CombatCondition')
    if not condition_comp:
        return []

    conditions = condition_comp.data.get('conditions', [])
    expired = []
    remaining = []

    for condition in conditions:
        duration_type = condition.get('duration_type')

        # Decrement duration for time-based conditions
        if duration_type == 'rounds' and end_of_turn:
            condition['duration_remaining'] -= 1
            if condition['duration_remaining'] <= 0:
                expired.append(condition['name'])
            else:
                remaining.append(condition)
        elif duration_type in ['permanent', 'concentration', 'until_save']:
            # These don't expire automatically
            remaining.append(condition)
        else:
            remaining.append(condition)

    # Update component
    if remaining:
        engine.update_component(entity_id, 'CombatCondition', {'conditions': remaining})
    else:
        # Remove component if no conditions remain
        engine.remove_component(entity_id, 'CombatCondition')

    return expired


__all__ = [
    'CombatEncounterComponent',
    'InitiativeComponent',
    'CombatConditionComponent',
    'calculate_ability_modifier',
    'get_attack_modifier',
    'get_spell_attack_modifier',
    'get_armor_class',
    'calculate_proficiency_bonus',
    'resolve_attack',
    'apply_damage',
    'apply_condition',
    'update_condition_durations'
]
