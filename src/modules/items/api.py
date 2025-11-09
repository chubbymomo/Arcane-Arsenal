"""
Items Module API Blueprint.

Provides REST API endpoints for inventory and equipment management.
This blueprint contains all inventory-related endpoints that were previously
in the core server.py, following the MODULE_GUIDE.md principle of "Don't Modify Core".

Endpoints:
- GET  /api/equipment/<entity_id>  - Get equipped items for an entity
- GET  /api/inventory/<entity_id>  - Get inventory (all owned items) for an entity
- POST /api/equip                  - Equip an item
- POST /api/unequip                - Unequip an item
"""

import logging
from flask import Blueprint, jsonify, request, session
from src.core.state_engine import StateEngine
from src.core.module_loader import ModuleLoader

logger = logging.getLogger(__name__)

# Create blueprint for items module API
items_bp = Blueprint('items', __name__)


def get_current_world_path():
    """Get current world path from session or return None."""
    return session.get('world_path')


def get_equipment_system(world_path: str):
    """
    Get initialized equipment system for a world.

    This helper function properly loads and initializes the items module
    with an engine instance, ensuring the equipment system is ready to use.

    Args:
        world_path: Path to the world directory

    Returns:
        EquipmentSystem instance

    Raises:
        ValueError: If items module is not loaded in this world
    """
    # Create engine instance
    engine = StateEngine(world_path)

    # Load and initialize modules with the engine
    loader = ModuleLoader(world_path)
    modules = loader.load_modules(strategy='config')

    # Initialize each module with the engine
    for module in modules:
        try:
            module.initialize(engine)
        except Exception as e:
            logger.warning(f"Failed to initialize module {module.name}: {e}")

    # Find items module
    items_module = None
    for module in modules:
        if module.name == 'items':
            items_module = module
            break

    if not items_module:
        raise ValueError('Items module not loaded in this world')

    return items_module.get_equipment_system()


@items_bp.route('/api/equipment/<entity_id>')
def api_equipment(entity_id: str):
    """
    JSON API: Get equipped items for an entity.

    Returns:
        {
            "success": true,
            "items": [
                {
                    "entity": {...},
                    "slot": "main_hand",
                    "components": {...}
                },
                ...
            ]
        }
    """
    world_path = get_current_world_path()
    if not world_path:
        return jsonify({'error': 'No world selected', 'success': False}), 400

    try:
        equipment_system = get_equipment_system(world_path)
        equipped_items = equipment_system.get_equipped_items(entity_id)

        return jsonify({
            'success': True,
            'items': [
                {
                    'entity': item['entity'].to_dict(),
                    'slot': item['slot'],
                    'components': item['components']
                }
                for item in equipped_items
            ]
        })

    except Exception as e:
        logger.error(f"Error getting equipment for entity {entity_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@items_bp.route('/api/inventory/<entity_id>')
def api_inventory(entity_id: str):
    """
    JSON API: Get inventory (all owned items) for an entity.

    Returns:
        {
            "success": true,
            "items": [
                {
                    "entity": {...},
                    "equipped": true/false,
                    "components": {...}
                },
                ...
            ]
        }
    """
    world_path = get_current_world_path()
    if not world_path:
        return jsonify({'error': 'No world selected', 'success': False}), 400

    try:
        equipment_system = get_equipment_system(world_path)
        inventory = equipment_system.get_inventory(entity_id)

        return jsonify({
            'success': True,
            'items': [
                {
                    'entity': item['entity'].to_dict(),
                    'equipped': item['equipped'],
                    'components': item['components']
                }
                for item in inventory
            ]
        })

    except Exception as e:
        logger.error(f"Error getting inventory for entity {entity_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@items_bp.route('/api/equip', methods=['POST'])
def api_equip_item():
    """
    JSON API: Equip an item.

    Request JSON:
        {
            "character_id": "entity_123",
            "item_id": "entity_456"
        }

    Returns:
        {
            "success": true,
            "data": {
                "character_id": "...",
                "item_id": "...",
                "slot": "main_hand"
            }
        }
    """
    world_path = get_current_world_path()
    if not world_path:
        return jsonify({'error': 'No world selected', 'success': False}), 400

    try:
        data = request.get_json()
        character_id = data.get('character_id')
        item_id = data.get('item_id')

        if not character_id or not item_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: character_id, item_id'
            }), 400

        equipment_system = get_equipment_system(world_path)
        result = equipment_system.equip_item(character_id, item_id)

        if result.success:
            return jsonify({
                'success': True,
                'data': result.data
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error
            }), 400

    except Exception as e:
        logger.error(f"Error equipping item: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@items_bp.route('/api/unequip', methods=['POST'])
def api_unequip_item():
    """
    JSON API: Unequip an item.

    Request JSON:
        {
            "character_id": "entity_123",
            "item_id": "entity_456"
        }

    Returns:
        {
            "success": true,
            "data": {
                "character_id": "...",
                "item_id": "..."
            }
        }
    """
    world_path = get_current_world_path()
    if not world_path:
        return jsonify({'error': 'No world selected', 'success': False}), 400

    try:
        data = request.get_json()
        character_id = data.get('character_id')
        item_id = data.get('item_id')

        if not character_id or not item_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: character_id, item_id'
            }), 400

        equipment_system = get_equipment_system(world_path)
        result = equipment_system.unequip_item(character_id, item_id)

        if result.success:
            return jsonify({
                'success': True,
                'data': result.data
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error
            }), 400

    except Exception as e:
        logger.error(f"Error unequipping item: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


__all__ = ['items_bp']
