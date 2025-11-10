"""
Generic Fantasy Module API Blueprint.

Provides REST API endpoints for fantasy-specific character creation and management.

Endpoints:
- POST /api/fantasy/character/create - Create a fantasy character with race, class, attributes
"""

import logging
from flask import Blueprint, jsonify, request, session, current_app
from src.core.module_loader import ModuleLoader

logger = logging.getLogger(__name__)

# Create blueprint for generic_fantasy module API
generic_fantasy_bp = Blueprint('generic_fantasy', __name__)

# Cache for initialized modules per world
_world_modules_cache = {}


def get_engine():
    """Get the cached StateEngine for the current world."""
    world_name = session.get('world_name')
    if not world_name:
        raise ValueError('No world selected')

    engine = current_app.engine_instances.get(world_name)
    if not engine:
        raise ValueError(f'StateEngine not initialized for world: {world_name}')

    return engine


def ensure_modules_loaded():
    """Ensure modules are loaded for the current world."""
    world_name = session.get('world_name')
    if not world_name:
        return

    if world_name not in _world_modules_cache:
        world_path = session.get('world_path')
        engine = get_engine()

        logger.info(f"Loading modules for world: {world_name}")
        loader = ModuleLoader(world_path)
        modules = loader.load_modules(strategy='config')

        for module in modules:
            try:
                module.initialize(engine)
            except Exception as e:
                logger.warning(f"Failed to initialize module {module.name}: {e}")

        _world_modules_cache[world_name] = modules
        logger.info(f"✓ Modules loaded: {world_name}")


@generic_fantasy_bp.route('/api/fantasy/character/create', methods=['POST'])
def api_create_character():
    """
    Create a fantasy character with race, class, and attributes.

    Request JSON:
        {
            "entity_id": "character_123",      # Entity must already exist
            "race": "elf",                     # Optional
            "character_class": "wizard",       # Optional
            "alignment": "chaotic_good",       # Optional
            "strength": 10,                    # Optional, 1-20
            "dexterity": 14,                   # Optional, 1-20
            "constitution": 12,                # Optional, 1-20
            "intelligence": 16,                # Optional, 1-20
            "wisdom": 13,                      # Optional, 1-20
            "charisma": 8                      # Optional, 1-20
        }

    Returns:
        {
            "success": true,
            "components_added": ["Attributes", "CharacterDetails", "Magic", "Skills"]
        }
    """
    try:
        ensure_modules_loaded()
        engine = get_engine()

        data = request.get_json()
        entity_id = data.get('entity_id')

        if not entity_id:
            return jsonify({
                'success': False,
                'error': 'Missing required field: entity_id'
            }), 400

        # Verify entity exists
        entity = engine.get_entity(entity_id)
        if not entity:
            return jsonify({
                'success': False,
                'error': f'Entity {entity_id} not found'
            }), 404

        components_added = []

        # Add Attributes component if attribute values provided
        strength = data.get('strength')
        dexterity = data.get('dexterity')
        constitution = data.get('constitution')
        intelligence = data.get('intelligence')
        wisdom = data.get('wisdom')
        charisma = data.get('charisma')

        attrs = [strength, dexterity, constitution, intelligence, wisdom, charisma]
        has_attributes = any(attr is not None for attr in attrs)

        if has_attributes:
            # Validate all attributes are present and in range
            if any(attr is None or attr < 1 or attr > 20 for attr in attrs):
                return jsonify({
                    'success': False,
                    'error': 'All attributes must be provided and between 1 and 20'
                }), 400

            result = engine.add_component(entity_id, 'Attributes', {
                'strength': strength,
                'dexterity': dexterity,
                'constitution': constitution,
                'intelligence': intelligence,
                'wisdom': wisdom,
                'charisma': charisma
            })

            if not result.success:
                return jsonify({
                    'success': False,
                    'error': f'Failed to add Attributes: {result.error}'
                }), 400

            components_added.append('Attributes')

        # Add CharacterDetails if race, class, or alignment provided
        race = data.get('race')
        char_class = data.get('character_class')
        alignment = data.get('alignment')

        if race or char_class or alignment:
            char_details = {
                'level': 1  # Default starting level
            }
            if race:
                char_details['race'] = race
            if char_class:
                char_details['character_class'] = char_class
            if alignment:
                char_details['alignment'] = alignment

            result = engine.add_component(entity_id, 'CharacterDetails', char_details)

            if not result.success:
                return jsonify({
                    'success': False,
                    'error': f'Failed to add CharacterDetails: {result.error}'
                }), 400

            components_added.append('CharacterDetails')

            # Event system will auto-add Magic and Skills components if spellcaster
            # (via component.added event handler in generic_fantasy module)

        if not components_added:
            return jsonify({
                'success': False,
                'error': 'No fantasy components specified (provide race, class, alignment, or attributes)'
            }), 400

        return jsonify({
            'success': True,
            'components_added': components_added,
            'message': f'Fantasy character components added to {entity.name}'
        })

    except ValueError as e:
        logger.error(f"Validation error creating fantasy character: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error creating fantasy character: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


__all__ = ['generic_fantasy_bp']
