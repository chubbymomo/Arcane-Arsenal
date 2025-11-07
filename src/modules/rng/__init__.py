"""
RNG Module - Random Number Generation for TTRPG dice rolls.

Provides:
- Dice notation parsing (1d20+5, 3d6, etc.)
- Advantage/disadvantage mechanics (D&D 5e)
- Critical success/failure detection
- Entity-specific modifiers (luck, bonuses)
- Event-driven roll processing
- Audit trail for all rolls

Usage:
    # Request a roll via event
    engine.event_bus.publish(Event(
        event_type='roll.requested',
        entity_id='player_123',
        data={
            'entity_id': 'player_123',
            'notation': '1d20+5',
            'roll_type': 'attack',
            'purpose': 'Attack goblin with sword'
        }
    ))

    # Subscribe to results
    def on_roll(event):
        print(event.data['breakdown'])  # "1d20+5: [13]+5 = 18"

    engine.event_bus.subscribe('roll.completed', on_roll)
"""

import logging
from typing import List, Dict, Any, Optional
from ..base import (
    Module,
    ComponentTypeDefinition,
    EventTypeDefinition,
    RollTypeDefinition
)
from src.core.event_bus import Event
from src.core.state_engine import StateEngine

from .components import LuckComponent, RollModifierComponent
from .events import roll_requested_event, roll_completed_event
from .roller import DiceRoller, RollResult
from .dice_parser import DiceParser, DiceNotationError
from .roll_types import core_roll_types

logger = logging.getLogger(__name__)


class RNGModule(Module):
    """
    Random Number Generation module for TTRPG dice rolls.

    Features:
    - Dice notation support (1d20, 3d6+5, 2d8+1d6+3)
    - Advantage/disadvantage (D&D 5e)
    - Critical hit/fail detection
    - Entity-specific modifiers
    - Event-driven architecture
    - Seeded random for determinism
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize RNG module.

        Args:
            seed: Optional random seed for deterministic rolls (testing/replay)
        """
        self.engine: Optional[StateEngine] = None
        self.roller = DiceRoller(seed=seed)

    @property
    def name(self) -> str:
        return "rng"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "Random Number Generation"

    @property
    def description(self) -> str:
        return "Dice rolling system with advantage/disadvantage and modifiers"

    @property
    def is_core(self) -> bool:
        return True  # Core module - always loaded

    def dependencies(self) -> List[str]:
        return []  # No dependencies

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        return [
            LuckComponent(),
            RollModifierComponent()
        ]

    def register_event_types(self) -> List[EventTypeDefinition]:
        return [
            roll_requested_event(),
            roll_completed_event()
        ]

    def register_roll_types(self) -> List['RollTypeDefinition']:
        """Register core roll types."""
        return core_roll_types()

    def initialize(self, engine: StateEngine) -> None:
        """Initialize module - subscribe to roll requests."""
        self.engine = engine

        # Subscribe to roll requests
        engine.event_bus.subscribe('roll.requested', self.on_roll_requested)

    def on_event(self, event: Event) -> None:
        """Handle events (called by engine)."""
        if event.event_type == 'roll.requested':
            self.on_roll_requested(event)

    def on_roll_requested(self, event: Event) -> None:
        """
        Process roll request.

        Steps:
        1. Parse request data
        2. Get entity modifiers (Luck, RollModifier components)
        3. Determine advantage/disadvantage
        4. Perform roll
        5. Publish result event
        """
        if not self.engine:
            return

        # Extract request data
        entity_id = event.data.get('entity_id')
        notation = event.data.get('notation')
        roll_type = event.data.get('roll_type')
        purpose = event.data.get('purpose', '')
        target_id = event.data.get('target_id')
        force_advantage = event.data.get('force_advantage', False)
        force_disadvantage = event.data.get('force_disadvantage', False)

        if not entity_id or not notation or not roll_type:
            # Invalid request
            return

        # Validate roll_type is registered
        registered_types = {rt['type'] for rt in self.engine.storage.get_roll_types()}
        if roll_type not in registered_types:
            logger.warning(
                f"Invalid roll_type '{roll_type}' for entity {entity_id}. "
                f"Must be one of: {', '.join(sorted(registered_types))}"
            )
            return

        try:
            # Get entity modifiers
            modifiers_applied = []
            total_bonus = 0
            advantage = force_advantage
            disadvantage = force_disadvantage

            # Check for Luck component
            luck = self.engine.get_component(entity_id, 'Luck')
            if luck:
                # Global bonus
                if luck.data.get('global_bonus', 0) != 0:
                    total_bonus += luck.data['global_bonus']
                    modifiers_applied.append({
                        'source': 'Luck',
                        'bonus': luck.data['global_bonus'],
                        'type': 'global'
                    })

                # Advantage/disadvantage from luck
                if roll_type in luck.data.get('advantage_on', []):
                    advantage = True
                if roll_type in luck.data.get('disadvantage_on', []):
                    disadvantage = True

            # Check for RollModifier components
            # Note: An entity can have multiple RollModifier components,
            # but our current system only allows one component per type.
            # In a real implementation, you might want to use relationships
            # to link entities to multiple modifier entities, or extend
            # the component system to allow multiple instances.
            roll_modifier = self.engine.get_component(entity_id, 'RollModifier')
            if roll_modifier and roll_modifier.data.get('modifier_type') == roll_type:
                bonus = roll_modifier.data.get('bonus', 0)
                if bonus != 0:
                    total_bonus += bonus
                    modifiers_applied.append({
                        'source': roll_modifier.data.get('source', 'Unknown'),
                        'bonus': bonus,
                        'type': roll_type
                    })

            # Apply total bonus to notation
            if total_bonus != 0:
                # Parse original notation
                parsed = DiceParser.parse(notation)
                # Add bonus to static modifier
                adjusted_modifier = parsed.static_modifier + total_bonus
                # Rebuild notation
                dice_part = '+'.join(str(dg) for dg in parsed.dice_groups)
                if adjusted_modifier > 0:
                    notation = f"{dice_part}+{adjusted_modifier}"
                elif adjusted_modifier < 0:
                    notation = f"{dice_part}{adjusted_modifier}"
                else:
                    notation = dice_part

            # Perform roll
            result = self.roller.roll(
                notation=notation,
                advantage=advantage and not disadvantage,
                disadvantage=disadvantage and not advantage,
                metadata={
                    'entity_id': entity_id,
                    'roll_type': roll_type,
                    'purpose': purpose,
                    'target_id': target_id
                }
            )

            # Publish result event
            self.engine.event_bus.publish(Event.create(
                event_type='roll.completed',
                entity_id=entity_id,
                actor_id=entity_id,
                data={
                    'entity_id': entity_id,
                    'notation': event.data.get('notation'),  # Original notation
                    'adjusted_notation': result.notation,    # With modifiers
                    'roll_type': roll_type,
                    'purpose': purpose,
                    'target_id': target_id,
                    'total': result.total,
                    'breakdown': result.get_breakdown(),
                    'advantage': result.advantage,
                    'disadvantage': result.disadvantage,
                    'natural_20': result.natural_20,
                    'natural_1': result.natural_1,
                    'modifiers_applied': modifiers_applied,
                    'dice_results': [
                        {
                            'expression': str(dr.expression),
                            'rolls': dr.rolls,
                            'total': dr.total
                        }
                        for dr in result.dice_results
                    ]
                }
            ))

        except (DiceNotationError, ValueError) as e:
            # Invalid notation or roll parameters
            logger.error(f"Roll error for entity {entity_id}, notation '{notation}': {e}")

    def roll_direct(
        self,
        notation: str,
        advantage: bool = False,
        disadvantage: bool = False
    ) -> RollResult:
        """
        Perform a roll directly without entity modifiers (for testing/scripting).

        Args:
            notation: Dice notation
            advantage: Roll with advantage
            disadvantage: Roll with disadvantage

        Returns:
            RollResult
        """
        return self.roller.roll(notation, advantage, disadvantage)
