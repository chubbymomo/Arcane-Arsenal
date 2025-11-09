"""
Spell utilities for data-driven spell management.

Provides functions to load, export, and manage spells as data rather than hardcoded.
DMs can add custom spells at campaign start or during gameplay.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def load_spells_from_file(engine, file_path: str, module_name: str = 'generic_fantasy') -> int:
    """
    Load spells from a JSON file into the spells registry.

    Args:
        engine: StateEngine instance
        file_path: Path to JSON file containing spell data
        module_name: Module that owns the spells registry (default: 'generic_fantasy')

    Returns:
        Number of spells loaded

    Example JSON format:
        {
          "spells": [
            {
              "key": "fireball",
              "description": "Fireball - 8d6 fire damage",
              "metadata": {
                "level": 3,
                "school": "evocation",
                "damage": "8d6",
                "damage_type": "fire"
              }
            }
          ]
        }
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Spell file not found: {file_path}")
            return 0

        with open(path, 'r') as f:
            data = json.load(f)

        spells_registry = engine.create_registry('spells', module_name)
        spells_data = data.get('spells', [])

        count = 0
        for spell in spells_data:
            key = spell.get('key')
            description = spell.get('description', '')
            metadata = spell.get('metadata', {})

            if key:
                spells_registry.register(key, description, metadata)
                count += 1
            else:
                logger.warning(f"Skipping spell without key: {spell}")

        logger.info(f"Loaded {count} spells from {file_path}")
        return count

    except Exception as e:
        logger.error(f"Error loading spells from {file_path}: {e}")
        return 0


def export_spells_to_file(engine, file_path: str, module_name: str = 'generic_fantasy') -> bool:
    """
    Export all spells from the registry to a JSON file.

    Useful for:
    - Backing up custom spells created during a campaign
    - Sharing spell lists between campaigns
    - Creating spell compendiums

    Args:
        engine: StateEngine instance
        file_path: Path to save JSON file
        module_name: Module that owns the spells registry

    Returns:
        True if export succeeded, False otherwise
    """
    try:
        spells_registry = engine.create_registry('spells', module_name)
        all_spells = spells_registry.get_all()

        spell_data = {
            'spells': [
                {
                    'key': spell['key'],
                    'description': spell['description'],
                    'metadata': spell.get('metadata', {})
                }
                for spell in all_spells
            ]
        }

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(spell_data, f, indent=2)

        logger.info(f"Exported {len(all_spells)} spells to {file_path}")
        return True

    except Exception as e:
        logger.error(f"Error exporting spells to {file_path}: {e}")
        return False


def add_spell(
    engine,
    key: str,
    description: str,
    metadata: Dict[str, Any],
    module_name: str = 'generic_fantasy'
) -> bool:
    """
    Add a single spell to the registry.

    Args:
        engine: StateEngine instance
        key: Unique spell identifier (e.g., 'fireball')
        description: Human-readable description
        metadata: Spell properties (level, school, damage, etc.)
        module_name: Module that owns the spells registry

    Returns:
        True if spell was added successfully

    Example:
        add_spell(engine, 'custom_bolt', 'Custom Bolt - 2d8 damage', {
            'level': 2,
            'school': 'evocation',
            'damage': '2d8',
            'damage_type': 'force'
        })
    """
    try:
        spells_registry = engine.create_registry('spells', module_name)
        spells_registry.register(key, description, metadata)
        logger.info(f"Added spell: {key}")
        return True
    except Exception as e:
        logger.error(f"Error adding spell {key}: {e}")
        return False


def get_spells_by_level(engine, level: int, module_name: str = 'generic_fantasy') -> List[Dict[str, Any]]:
    """
    Get all spells of a specific level.

    Args:
        engine: StateEngine instance
        level: Spell level (0-9, where 0 is cantrips)
        module_name: Module that owns the spells registry

    Returns:
        List of spell dictionaries filtered by level
    """
    try:
        spells_registry = engine.create_registry('spells', module_name)
        all_spells = spells_registry.get_all()

        return [
            spell for spell in all_spells
            if spell.get('metadata', {}).get('level') == level
        ]
    except Exception as e:
        logger.error(f"Error getting spells by level {level}: {e}")
        return []


def get_spells_by_school(engine, school: str, module_name: str = 'generic_fantasy') -> List[Dict[str, Any]]:
    """
    Get all spells from a specific school of magic.

    Args:
        engine: StateEngine instance
        school: School of magic (e.g., 'evocation', 'abjuration')
        module_name: Module that owns the spells registry

    Returns:
        List of spell dictionaries from the specified school
    """
    try:
        spells_registry = engine.create_registry('spells', module_name)
        all_spells = spells_registry.get_all()

        return [
            spell for spell in all_spells
            if spell.get('metadata', {}).get('school', '').lower() == school.lower()
        ]
    except Exception as e:
        logger.error(f"Error getting spells by school {school}: {e}")
        return []


def remove_spell(engine, key: str, module_name: str = 'generic_fantasy') -> bool:
    """
    Remove a spell from the registry.

    Useful for campaign-specific spell removal or spell banning.

    Args:
        engine: StateEngine instance
        key: Spell key to remove
        module_name: Module that owns the spells registry

    Returns:
        True if spell was removed successfully
    """
    try:
        spells_registry = engine.create_registry('spells', module_name)
        # Note: Registry doesn't have a built-in remove, but we could add one
        # For now, log the intention
        logger.info(f"Spell removal requested: {key}")
        # This would need to be implemented in the Registry class
        logger.warning("Spell removal not yet implemented in Registry class")
        return False
    except Exception as e:
        logger.error(f"Error removing spell {key}: {e}")
        return False


__all__ = [
    'load_spells_from_file',
    'export_spells_to_file',
    'add_spell',
    'get_spells_by_level',
    'get_spells_by_school',
    'remove_spell'
]
