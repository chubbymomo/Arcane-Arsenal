"""
Core dice rolling logic with advantage/disadvantage and critical detection.
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .dice_parser import DiceParser, ParsedRoll, DiceExpression


@dataclass
class DiceGroupResult:
    """Result from rolling a group of dice."""
    expression: DiceExpression  # What was rolled
    rolls: List[int]            # Individual die results
    total: int                  # Sum of rolls

    def __str__(self) -> str:
        rolls_str = ','.join(str(r) for r in self.rolls)
        return f"{self.expression} → [{rolls_str}] = {self.total}"


@dataclass
class RollResult:
    """Complete result of a dice roll."""
    notation: str                          # Original notation
    dice_results: List[DiceGroupResult]    # Results per dice group
    static_modifier: int                   # Static bonus/penalty
    total: int                             # Final total
    advantage: bool = False                # Was advantage used?
    disadvantage: bool = False             # Was disadvantage used?
    advantage_rolls: Optional[List[int]] = None  # If advantage: both d20 rolls
    natural_20: bool = False               # Critical success (nat 20)
    natural_1: bool = False                # Critical failure (nat 1)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context

    @property
    def is_critical_success(self) -> bool:
        """True if any d20 rolled a natural 20."""
        return self.natural_20

    @property
    def is_critical_failure(self) -> bool:
        """True if any d20 rolled a natural 1."""
        return self.natural_1

    def get_breakdown(self) -> str:
        """Human-readable breakdown of the roll."""
        parts = []

        if self.advantage or self.disadvantage:
            adv_type = "advantage" if self.advantage else "disadvantage"
            if self.advantage_rolls:
                rolls_str = ', '.join(str(r) for r in self.advantage_rolls)
                kept = max(self.advantage_rolls) if self.advantage else min(self.advantage_rolls)
                parts.append(f"1d20 with {adv_type}: [{rolls_str}] → kept {kept}")

        for dice_result in self.dice_results:
            rolls_str = ','.join(str(r) for r in dice_result.rolls)
            parts.append(f"{dice_result.expression.count}d{dice_result.expression.sides}: [{rolls_str}] = {dice_result.total}")

        if self.static_modifier != 0:
            parts.append(f"modifier: {self.static_modifier:+d}")

        parts.append(f"**Total: {self.total}**")

        if self.natural_20:
            parts.append("🎯 CRITICAL SUCCESS!")
        elif self.natural_1:
            parts.append("💀 CRITICAL FAILURE!")

        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event data."""
        return {
            'notation': self.notation,
            'total': self.total,
            'breakdown': self.get_breakdown(),
            'advantage': self.advantage,
            'disadvantage': self.disadvantage,
            'advantage_rolls': self.advantage_rolls,
            'natural_20': self.natural_20,
            'natural_1': self.natural_1,
            'dice_results': [
                {
                    'expression': str(dr.expression),
                    'rolls': dr.rolls,
                    'total': dr.total
                }
                for dr in self.dice_results
            ],
            'static_modifier': self.static_modifier,
            'metadata': self.metadata
        }


class DiceRoller:
    """
    Handles dice rolling with TTRPG-specific features.

    Supports:
    - Standard dice notation (1d20, 3d6+5, etc.)
    - Advantage/disadvantage (D&D 5e)
    - Critical hit/fail detection
    - Seeded random for determinism
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize roller.

        Args:
            seed: Random seed for deterministic rolls (testing/replay)
        """
        self.rng = random.Random(seed)
        self.seed = seed

    def roll(
        self,
        notation: str,
        advantage: bool = False,
        disadvantage: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RollResult:
        """
        Roll dice according to notation.

        Args:
            notation: Dice notation (e.g., "1d20+5", "3d6", "2d8+1d6+3")
            advantage: Roll twice, keep higher (for d20 only)
            disadvantage: Roll twice, keep lower (for d20 only)
            metadata: Additional context (purpose, entity_id, etc.)

        Returns:
            RollResult with complete breakdown

        Raises:
            DiceNotationError: If notation is invalid
            ValueError: If both advantage and disadvantage are True
        """
        if advantage and disadvantage:
            raise ValueError("Cannot have both advantage and disadvantage")

        # Parse notation
        parsed = DiceParser.parse(notation)

        # Roll each dice group
        dice_results = []
        advantage_rolls = None
        natural_20 = False
        natural_1 = False

        for i, dice_expr in enumerate(parsed.dice_groups):
            # Special handling for d20 with advantage/disadvantage
            if (advantage or disadvantage) and dice_expr.sides == 20 and dice_expr.count == 1 and i == 0:
                # Roll twice
                roll1 = self._roll_die(20)
                roll2 = self._roll_die(20)
                advantage_rolls = [roll1, roll2]

                # Keep appropriate roll
                kept_roll = max(roll1, roll2) if advantage else min(roll1, roll2)
                rolls = [kept_roll]

                # Check for natural 20/1 on EITHER roll
                natural_20 = (20 in advantage_rolls)
                natural_1 = (1 in advantage_rolls)
            else:
                # Normal roll
                rolls = [self._roll_die(dice_expr.sides) for _ in range(dice_expr.count)]

                # Check for natural 20/1 on d20s
                if dice_expr.sides == 20:
                    natural_20 = natural_20 or (20 in rolls)
                    natural_1 = natural_1 or (1 in rolls)

            dice_results.append(DiceGroupResult(
                expression=dice_expr,
                rolls=rolls,
                total=sum(rolls)
            ))

        # Calculate total
        dice_total = sum(dr.total for dr in dice_results)
        total = dice_total + parsed.static_modifier

        return RollResult(
            notation=parsed.original_notation,
            dice_results=dice_results,
            static_modifier=parsed.static_modifier,
            total=total,
            advantage=advantage,
            disadvantage=disadvantage,
            advantage_rolls=advantage_rolls,
            natural_20=natural_20,
            natural_1=natural_1,
            metadata=metadata or {}
        )

    def roll_simple(self, count: int, sides: int) -> List[int]:
        """
        Roll dice without parsing notation.

        Args:
            count: Number of dice
            sides: Number of sides per die

        Returns:
            List of individual rolls
        """
        return [self._roll_die(sides) for _ in range(count)]

    def _roll_die(self, sides: int) -> int:
        """Roll a single die."""
        return self.rng.randint(1, sides)

    def set_seed(self, seed: int):
        """Change random seed (for testing/replay)."""
        self.seed = seed
        self.rng = random.Random(seed)
