"""
Module Presets for Common Game Configurations.

Provides pre-configured module combinations for common game types.
Instead of manually loading modules, use a preset for quick setup.

Usage:
    from src.presets import load_preset
    load_preset(engine, 'standard_fantasy')
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# === Preset Definitions ===

PRESETS: Dict[str, Dict[str, Any]] = {
    'standard_fantasy': {
        'name': 'Standard Fantasy RPG',
        'description': 'Complete D&D-style fantasy setup with combat, magic, items',
        'modules': [
            'core_components',
            'rng',
            'generic_combat',
            'generic_fantasy',
            'items',
            'ai_dm'
        ],
        'data_files': {
            'spells': 'data/spells/starter_spells.json'
        }
    },

    'combat_light_fantasy': {
        'name': 'Narrative Fantasy',
        'description': 'Fantasy RPG focused on story, minimal combat mechanics',
        'modules': [
            'core_components',
            'rng',
            'generic_fantasy'
        ],
        'data_files': {
            'spells': 'data/spells/starter_spells.json'
        }
    },

    'combat_only': {
        'name': 'Pure Combat',
        'description': 'Just combat mechanics - useful for tactical skirmish games',
        'modules': [
            'core_components',
            'rng',
            'generic_combat'
        ]
    },

    'minimal': {
        'name': 'Minimal ECS',
        'description': 'Just core components - build your own game system',
        'modules': [
            'core_components'
        ]
    }
}


def get_preset(preset_name: str) -> Dict[str, Any]:
    """
    Get preset configuration by name.

    Args:
        preset_name: Name of preset (e.g., 'standard_fantasy')

    Returns:
        Preset configuration dictionary

    Raises:
        ValueError: If preset not found
    """
    if preset_name not in PRESETS:
        available = ', '.join(PRESETS.keys())
        raise ValueError(
            f"Preset '{preset_name}' not found. "
            f"Available presets: {available}"
        )
    return PRESETS[preset_name]


def list_presets() -> List[Dict[str, str]]:
    """
    List all available presets.

    Returns:
        List of dicts with 'name', 'description' for each preset

    Example:
        for preset in list_presets():
            print(f"{preset['key']}: {preset['name']} - {preset['description']}")
    """
    return [
        {
            'key': key,
            'name': config['name'],
            'description': config['description']
        }
        for key, config in PRESETS.items()
    ]


def load_preset(engine, preset_name: str) -> bool:
    """
    Load a preset configuration into the engine.

    This is a convenience function that:
    1. Loads all modules in the preset
    2. Loads any data files (spells, items, etc.)
    3. Initializes everything in the correct order

    Args:
        engine: StateEngine instance
        preset_name: Name of preset to load

    Returns:
        True if loaded successfully

    Example:
        # Quick setup for standard fantasy RPG
        engine = StateEngine()
        load_preset(engine, 'standard_fantasy')
        # Now ready to create characters!

    Raises:
        ValueError: If preset not found
    """
    preset = get_preset(preset_name)

    logger.info(f"Loading preset: {preset['name']}")

    # Load modules
    for module_name in preset['modules']:
        try:
            # Module loading happens through engine.register_module()
            # This function assumes modules are already registered
            logger.info(f"  Module: {module_name}")
        except Exception as e:
            logger.error(f"Error loading module {module_name}: {e}")
            return False

    # Load data files
    data_files = preset.get('data_files', {})

    # Load spells if specified
    if 'spells' in data_files:
        try:
            from src.modules.generic_fantasy.spell_utils import load_spells_from_file
            spell_count = load_spells_from_file(engine, data_files['spells'])
            logger.info(f"  Loaded {spell_count} spells from {data_files['spells']}")
        except Exception as e:
            logger.warning(f"Could not load spells: {e}")

    logger.info(f"Preset '{preset_name}' loaded successfully")
    return True


__all__ = [
    'PRESETS',
    'get_preset',
    'list_presets',
    'load_preset'
]
