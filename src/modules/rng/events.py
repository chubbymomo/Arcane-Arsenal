"""
Event definitions for RNG module.
"""

from typing import Dict, Any
from src.modules.base import EventTypeDefinition


# Event type definitions for RNG module
# These are factory functions that return EventTypeDefinition instances

def roll_requested_event() -> EventTypeDefinition:
    """
    Event published when an entity wants to make a roll.

    This triggers the RNG system to process the roll with all applicable modifiers.
    """
    return EventTypeDefinition(
        type="roll.requested",
        description="Request to roll dice for an entity",
        module="rng",
        data_schema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Entity making the roll"
                },
                "notation": {
                    "type": "string",
                    "description": "Dice notation (1d20+5, 3d6, etc.)"
                },
                "roll_type": {
                    "type": "string",
                    "description": "Type of roll (attack, damage, saving_throw, skill_check, etc.)",
                    "examples": ["attack", "damage", "saving_throw", "skill_check", "initiative"]
                },
                "purpose": {
                    "type": "string",
                    "description": "Human-readable purpose",
                    "default": ""
                },
                "target_id": {
                    "type": "string",
                    "description": "Optional target entity",
                    "default": None
                },
                "force_advantage": {
                    "type": "boolean",
                    "description": "Force advantage regardless of entity modifiers",
                    "default": False
                },
                "force_disadvantage": {
                    "type": "boolean",
                    "description": "Force disadvantage regardless of entity modifiers",
                    "default": False
                }
            },
            "required": ["entity_id", "notation", "roll_type"]
        }
    )


def roll_completed_event() -> EventTypeDefinition:
    """
    Event published when a roll is completed.

    Contains full breakdown of the roll for display and audit trail.
    """
    return EventTypeDefinition(
        type="roll.completed",
        description="Result of a completed dice roll",
        module="rng",
        data_schema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Entity that made the roll"
                },
                "notation": {
                    "type": "string",
                    "description": "Original dice notation"
                },
                "roll_type": {
                    "type": "string",
                    "description": "Type of roll"
                },
                "purpose": {
                    "type": "string",
                    "description": "Human-readable purpose"
                },
                "total": {
                    "type": "integer",
                    "description": "Final result"
                },
                "breakdown": {
                    "type": "string",
                    "description": "Human-readable breakdown"
                },
                "advantage": {
                    "type": "boolean",
                    "description": "Was advantage used?"
                },
                "disadvantage": {
                    "type": "boolean",
                    "description": "Was disadvantage used?"
                },
                "natural_20": {
                    "type": "boolean",
                    "description": "Did any d20 roll a natural 20?"
                },
                "natural_1": {
                    "type": "boolean",
                    "description": "Did any d20 roll a natural 1?"
                },
                "modifiers_applied": {
                    "type": "array",
                    "description": "List of modifiers that affected this roll",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "bonus": {"type": "integer"},
                            "type": {"type": "string"}
                        }
                    }
                },
                "dice_results": {
                    "type": "array",
                    "description": "Individual dice group results"
                }
            },
            "required": ["entity_id", "notation", "roll_type", "total", "breakdown"]
        }
    )
