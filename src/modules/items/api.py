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
from flask import Blueprint, jsonify, request, session, current_app
from src.core.module_loader import ModuleLoader

logger = logging.getLogger(__name__)

# Create blueprint for items module API
items_bp = Blueprint('items', __name__)

# Cache for initialized modules per world
# Modules are expensive to load (importing files, registering types, initializing registries)
# We load them once per world and reuse the same module instances
_world_modules_cache = {}


def get_equipment_system():
    """
    Get the equipment system for the current world.

    Uses Flask's cached StateEngine from current_app.engine_instances.
    Loads and initializes modules once per world, then reuses them.

    Returns:
        EquipmentSystem instance

    Raises:
        ValueError: If no world selected or items module not loaded
    """
    world_name = session.get('world_name')
    if not world_name:
        raise ValueError('No world selected')

    # Get the cached StateEngine for this world
    engine = current_app.engine_instances.get(world_name)
    if not engine:
        raise ValueError(f'StateEngine not initialized for world: {world_name}')

    # Check if modules are already loaded for this world
    if world_name not in _world_modules_cache:
        # Load and initialize modules (expensive - do once per world)
        world_path = session.get('world_path')
        logger.info(f"Loading modules for world: {world_name}")

        loader = ModuleLoader(world_path)
        modules = loader.load_modules(strategy='config')

        # Initialize each module with the cached engine
        for module in modules:
            try:
                module.initialize(engine)
            except Exception as e:
                logger.warning(f"Failed to initialize module {module.name}: {e}")

        # Cache the loaded modules for this world
        _world_modules_cache[world_name] = modules
        logger.info(f"✓ Modules loaded and cached for world: {world_name}")

    # Get modules from cache
    modules = _world_modules_cache[world_name]

    # Find items module
    for module in modules:
        if module.name == 'items':
            return module.get_equipment_system()

    raise ValueError('Items module not loaded in this world')


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
    try:
        equipment_system = get_equipment_system()
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
    try:
        equipment_system = get_equipment_system()
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
    try:
        data = request.get_json()
        character_id = data.get('character_id')
        item_id = data.get('item_id')

        if not character_id or not item_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: character_id, item_id'
            }), 400

        equipment_system = get_equipment_system()
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
    try:
        data = request.get_json()
        character_id = data.get('character_id')
        item_id = data.get('item_id')

        if not character_id or not item_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: character_id, item_id'
            }), 400

        equipment_system = get_equipment_system()
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


@items_bp.route('/api/inventory_display/<entity_id>')
def api_inventory_display(entity_id: str):
    """
    HTML API: Get rendered inventory display for an entity.

    This endpoint returns just the inventory display HTML without reloading
    the entire page, allowing for smooth updates without WebSocket reconnection.

    Returns:
        HTML string of the inventory display
    """
    try:
        world_name = session.get('world_name')
        if not world_name:
            return '<p>Error: No world selected</p>', 400

        # Get the cached StateEngine for this world
        engine = current_app.engine_instances.get(world_name)
        if not engine:
            return '<p>Error: StateEngine not initialized</p>', 500

        # Get entity to verify it exists
        entity = engine.get_entity(entity_id)
        if not entity:
            return '<p>Error: Entity not found</p>', 404

        # Get InventoryDisplay component
        inventory_display = engine.get_component(entity_id, 'InventoryDisplay')
        if not inventory_display:
            return '<p>No inventory display component found</p>', 404

        # Get the component definition to call its renderer
        comp_def = engine.component_validators.get('InventoryDisplay')
        if not comp_def:
            return '<p>Error: InventoryDisplay component definition not found</p>', 500

        # Render the inventory display
        html = comp_def.get_character_sheet_renderer(
            inventory_display.data,
            engine,
            entity_id
        )

        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    except Exception as e:
        logger.error(f"Error rendering inventory display for entity {entity_id}: {e}", exc_info=True)
        return f'<p>Error: {str(e)}</p>', 500


__all__ = ['items_bp']
