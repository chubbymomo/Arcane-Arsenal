"""
Dice notation parser for TTRPG dice rolls.

Supports standard dice notation:
- 1d20 (single die)
- 3d6+5 (multiple dice with modifier)
- 2d8+1d6+3 (complex expressions)
- Future: 4d6k3 (keep highest), 1d20r1 (reroll), etc.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DiceExpression:
    """Parsed dice expression."""
    count: int           # Number of dice
    sides: int           # Number of sides per die
    modifier: int = 0    # Static modifier

    def __str__(self) -> str:
        if self.modifier > 0:
            return f"{self.count}d{self.sides}+{self.modifier}"
        elif self.modifier < 0:
            return f"{self.count}d{self.sides}{self.modifier}"
        else:
            return f"{self.count}d{self.sides}"


@dataclass
class ParsedRoll:
    """Complete parsed roll expression."""
    dice_groups: List[DiceExpression]  # All dice groups
    static_modifier: int               # Final static bonus
    original_notation: str             # Original string

    def __str__(self) -> str:
        return self.original_notation


class DiceNotationError(Exception):
    """Raised when dice notation is invalid."""
    pass


class DiceParser:
    """Parser for TTRPG dice notation."""

    # Regex patterns
    DICE_PATTERN = re.compile(r'(\d+)d(\d+)', re.IGNORECASE)
    MODIFIER_PATTERN = re.compile(r'([+-]\d+)')

    @classmethod
    def parse(cls, notation: str) -> ParsedRoll:
        """
        Parse dice notation into structured format.

        Examples:
            "1d20" → ParsedRoll(dice_groups=[DiceExpression(1, 20, 0)], ...)
            "3d6+5" → ParsedRoll(dice_groups=[DiceExpression(3, 6, 0)], static_modifier=5, ...)
            "2d8+1d6+3" → ParsedRoll(dice_groups=[DiceExpression(2, 8), DiceExpression(1, 6)], ...)

        Args:
            notation: Dice notation string

        Returns:
            ParsedRoll object

        Raises:
            DiceNotationError: If notation is invalid
        """
        if not notation or not isinstance(notation, str):
            raise DiceNotationError("Notation must be a non-empty string")

        # Normalize: remove spaces, lowercase
        notation = notation.strip().replace(' ', '').lower()

        if not notation:
            raise DiceNotationError("Notation cannot be empty")

        # Find all dice expressions (e.g., "2d6", "1d20")
        dice_matches = cls.DICE_PATTERN.findall(notation)
        if not dice_matches:
            raise DiceNotationError(f"No valid dice expression found in '{notation}'")

        dice_groups = []
        for count_str, sides_str in dice_matches:
            count = int(count_str)
            sides = int(sides_str)

            # Validate
            if count < 1:
                raise DiceNotationError(f"Dice count must be at least 1, got {count}")
            if count > 100:
                raise DiceNotationError(f"Dice count too large (max 100), got {count}")
            if sides < 2:
                raise DiceNotationError(f"Dice must have at least 2 sides, got {sides}")
            if sides > 1000:
                raise DiceNotationError(f"Dice sides too large (max 1000), got {sides}")

            dice_groups.append(DiceExpression(count, sides))

        # Find static modifiers by removing dice expressions first
        # This prevents "2d8+1d6+3" from treating "+1" (from 1d6) as a modifier
        remaining = cls.DICE_PATTERN.sub('', notation)  # Remove all dice expressions
        modifier_matches = cls.MODIFIER_PATTERN.findall(remaining)
        static_modifier = sum(int(m) for m in modifier_matches)

        return ParsedRoll(
            dice_groups=dice_groups,
            static_modifier=static_modifier,
            original_notation=notation
        )

    @classmethod
    def validate(cls, notation: str) -> bool:
        """
        Check if notation is valid without parsing.

        Args:
            notation: Dice notation string

        Returns:
            True if valid, False otherwise
        """
        try:
            cls.parse(notation)
            return True
        except DiceNotationError:
            return False
