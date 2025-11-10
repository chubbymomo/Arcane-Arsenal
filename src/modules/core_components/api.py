"""
Core Components Module API Blueprint.

Provides REST API endpoints for core component functionality like position queries.

Endpoints:
- GET /api/position/world/<entity_id> - Get world position for an entity
- GET /api/position/nearby/<entity_id> - Get nearby entities in same region
"""

import logging
from flask import Blueprint, jsonify, session, current_app
from src.core.module_loader import ModuleLoader

logger = logging.getLogger(__name__)

# Create blueprint for core_components module API
core_components_bp = Blueprint('core_components', __name__)

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


def get_position_system():
    """Get the PositionSystem for the current world."""
    from .systems import PositionSystem
    engine = get_engine()
    return PositionSystem(engine)


@core_components_bp.route('/api/position/world/<entity_id>')
def api_world_position(entity_id: str):
    """
    Get the absolute world position for an entity.

    Resolves hierarchical positions (e.g., item in chest in tavern) to absolute coordinates.

    Returns:
        {
            "success": true,
            "entity_id": "character_123",
            "world_position": [100.5, 200.0, 0.0]  # or null if no position
        }
    """
    try:
        position_system = get_position_system()
        world_pos = position_system.get_world_position(entity_id)

        return jsonify({
            'success': True,
            'entity_id': entity_id,
            'world_position': list(world_pos) if world_pos else None
        })

    except Exception as e:
        logger.error(f"Error getting world position for entity {entity_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@core_components_bp.route('/api/position/nearby/<entity_id>')
def api_nearby_entities(entity_id: str):
    """
    Get entities in the same region as the specified entity.

    Returns:
        {
            "success": true,
            "entity_id": "character_123",
            "region": "tavern_main_room",
            "nearby_entities": [
                {"id": "npc_456", "name": "Barkeep"},
                {"id": "item_789", "name": "Sword on table"}
            ]
        }
    """
    try:
        engine = get_engine()
        position_system = get_position_system()

        # Get the entity's position
        position = engine.get_component(entity_id, 'Position')
        if not position:
            return jsonify({
                'success': False,
                'error': f'Entity {entity_id} has no Position component'
            }), 404

        region = position.data.get('region')
        if not region:
            return jsonify({
                'success': True,
                'entity_id': entity_id,
                'region': None,
                'nearby_entities': []
            })

        # Get all entities in the region
        nearby_entity_ids = position_system.get_entities_in_region(region)

        # Convert to entity objects (exclude the query entity itself)
        nearby_entities = []
        for e_id in nearby_entity_ids:
            if e_id != entity_id:
                nearby_entity = engine.get_entity(e_id)
                if nearby_entity and nearby_entity.is_active():
                    nearby_entities.append({
                        'id': nearby_entity.id,
                        'name': nearby_entity.name
                    })

        return jsonify({
            'success': True,
            'entity_id': entity_id,
            'region': region,
            'nearby_entities': nearby_entities
        })

    except Exception as e:
        logger.error(f"Error getting nearby entities for {entity_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


__all__ = ['core_components_bp']
