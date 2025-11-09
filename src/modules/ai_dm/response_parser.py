"""
Response Parser for AI DM.

Extracts narrative text and suggested actions from LLM responses.
Handles various response formats and provides fallback actions.
"""

import re
import json
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def parse_dm_response(raw_response: str) -> Tuple[str, List[Dict]]:
    """
    Parse DM response into narrative text and suggested actions.

    Expects responses in the format:
        Narrative text here...

        <actions>
        [JSON array of action objects]
        </actions>

    Args:
        raw_response: Raw text from LLM

    Returns:
        Tuple of (narrative_text, suggested_actions)

    Example:
        >>> response = '''
        ... You enter the tavern...
        ...
        ... <actions>
        ... [{"label": "🎲 Roll Perception", "action_type": "roll_dice", ...}]
        ... </actions>
        ... '''
        >>> narrative, actions = parse_dm_response(response)
        >>> print(narrative)
        You enter the tavern...
        >>> print(len(actions))
        1
    """
    logger.debug(f"Parsing response: {len(raw_response)} characters")

    # Extract actions section
    actions_match = re.search(
        r'<actions>\s*(.*?)\s*</actions>',
        raw_response,
        re.DOTALL | re.IGNORECASE
    )

    suggested_actions = []
    if actions_match:
        actions_json = actions_match.group(1).strip()

        try:
            suggested_actions = json.loads(actions_json)
            logger.info(f"Parsed {len(suggested_actions)} actions from response")

            # Validate action format
            suggested_actions = [
                action for action in suggested_actions
                if validate_action(action)
            ]

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse actions JSON: {e}")
            logger.debug(f"Malformed JSON: {actions_json}")
            suggested_actions = get_fallback_actions()

        # Remove actions section from narrative
        narrative = raw_response[:actions_match.start()].strip()
    else:
        logger.info("No actions section found in response, using full text as narrative")
        narrative = raw_response.strip()
        suggested_actions = get_fallback_actions()

    # Clean up narrative
    narrative = clean_narrative(narrative)

    # Ensure we always have at least some actions
    if not suggested_actions or len(suggested_actions) == 0:
        logger.warning("No valid actions in response, using fallbacks")
        suggested_actions = get_fallback_actions()

    logger.debug(f"Final parse: {len(narrative)} chars narrative, {len(suggested_actions)} actions")
    return narrative, suggested_actions


def validate_action(action: Dict) -> bool:
    """
    Validate that an action has required fields and safe data.

    Args:
        action: Action dict to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ['label', 'action_type']

    for field in required_fields:
        if field not in action:
            logger.warning(f"Action missing required field '{field}': {action}")
            return False

    # Check action_type is valid
    valid_types = ['roll_dice', 'custom']
    if action['action_type'] not in valid_types:
        logger.warning(f"Invalid action_type '{action['action_type']}': must be one of {valid_types}")
        return False

    # Validate action_data exists and is a dict
    if 'action_data' in action and not isinstance(action.get('action_data'), dict):
        logger.warning(f"action_data must be a dict: {action}")
        return False

    # Ensure action_data can be safely JSON-serialized
    if 'action_data' in action:
        try:
            json.dumps(action['action_data'])
        except (TypeError, ValueError) as e:
            logger.warning(f"action_data cannot be JSON-serialized: {e}")
            return False

    # Validate string fields don't contain problematic characters for HTML/JS
    label = action.get('label', '')
    if not isinstance(label, str):
        logger.warning(f"label must be a string: {action}")
        return False

    return True


def clean_narrative(text: str) -> str:
    """
    Clean up narrative text.

    Removes extra whitespace, fixes common formatting issues.

    Args:
        text: Raw narrative text

    Returns:
        Cleaned narrative text
    """
    # Remove multiple blank lines
    text = re.sub(r'\n\n\n+', '\n\n', text)

    # Remove leading/trailing whitespace from lines
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # Remove leading/trailing whitespace overall
    text = text.strip()

    return text


def get_fallback_actions() -> List[Dict]:
    """
    Get default fallback actions when LLM doesn't provide them.

    Returns:
        List of generic actions suitable for most situations
    """
    return [
        {
            'label': '🔍 Look Around',
            'action_type': 'roll_dice',
            'action_data': {
                'dice': '1d20',
                'label': 'Perception Check'
            }
        },
        {
            'label': '💬 Talk',
            'action_type': 'custom',
            'action_data': {
                'action': 'initiate_dialogue'
            }
        },
        {
            'label': '🚶 Move',
            'action_type': 'custom',
            'action_data': {
                'action': 'move'
            }
        }
    ]


def extract_dice_notation(action: Dict) -> str:
    """
    Extract dice notation from a roll_dice action.

    Args:
        action: Action dict with roll_dice type

    Returns:
        Dice notation string (e.g., "1d20+3")

    Example:
        >>> action = {
        ...     'action_type': 'roll_dice',
        ...     'action_data': {'dice': '1d20+3', 'label': 'Attack'}
        ... }
        >>> extract_dice_notation(action)
        '1d20+3'
    """
    if action.get('action_type') != 'roll_dice':
        return ''

    action_data = action.get('action_data', {})
    return action_data.get('dice', '1d20')


def format_actions_for_display(actions: List[Dict]) -> str:
    """
    Format actions as human-readable text (for debugging/logging).

    Args:
        actions: List of action dicts

    Returns:
        Formatted string

    Example:
        >>> actions = [
        ...     {'label': '🎲 Roll Perception', 'action_type': 'roll_dice', ...}
        ... ]
        >>> print(format_actions_for_display(actions))
        1. 🎲 Roll Perception (roll_dice)
    """
    lines = []
    for i, action in enumerate(actions, 1):
        label = action.get('label', 'Unknown')
        action_type = action.get('action_type', 'unknown')
        lines.append(f"{i}. {label} ({action_type})")

    return '\n'.join(lines)


__all__ = [
    'parse_dm_response',
    'validate_action',
    'clean_narrative',
    'get_fallback_actions',
    'extract_dice_notation',
    'format_actions_for_display'
]
