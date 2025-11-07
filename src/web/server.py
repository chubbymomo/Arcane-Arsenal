"""
Web interface for Arcane Arsenal.

Flask app with separate client (player) and host (DM) interfaces.
- /: World selector landing page
- /client: Player interface for character management
- /host: DM interface for full state management
- WebSocket support for real-time updates
"""

import logging
from flask import Flask, jsonify, request, redirect, url_for, session, render_template, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.state_engine import StateEngine
from src.core.module_loader import ModuleLoader
from src.core.models import Event
from src.web.blueprints import client_bp, host_bp

logger = logging.getLogger(__name__)

# Global SocketIO instance
socketio = None


def create_app(worlds_dir: str = 'worlds'):
    """
    Create Flask app with SocketIO support for real-time features.

    Args:
        worlds_dir: Directory containing world folders (default: 'worlds')

    Returns:
        Tuple of (Flask app, SocketIO instance)
    """
    global socketio

    app = Flask(__name__)
    app.config['WORLDS_DIR'] = worlds_dir
    app.config['SECRET_KEY'] = os.urandom(24)  # For sessions and flash messages

    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",  # Configure appropriately for production
        async_mode='eventlet',
        logger=True,
        engineio_logger=False
    )

    # Register blueprints
    app.register_blueprint(client_bp)
    app.register_blueprint(host_bp)

    # Helper: Get list of available worlds
    def get_available_worlds():
        """Return list of world directories with their metadata."""
        if not os.path.exists(worlds_dir):
            return []

        worlds = []
        for item in os.listdir(worlds_dir):
            world_path = os.path.join(worlds_dir, item)
            db_path = os.path.join(world_path, 'world.db')
            config_path = os.path.join(world_path, 'config.json')

            if os.path.isdir(world_path) and os.path.exists(db_path):
                world_info = {'name': item, 'path': world_path}

                # Try to read world name from config
                if os.path.exists(config_path):
                    try:
                        import json
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            world_info['display_name'] = config.get('world_name', item)
                    except Exception as e:
                        logger.warning(f"Failed to read config for world '{item}': {e}")
                        world_info['display_name'] = item
                else:
                    world_info['display_name'] = item

                worlds.append(world_info)

        return sorted(worlds, key=lambda w: w['name'])

    # Root route - World selector
    @app.route('/')
    def index():
        """World selection landing page."""
        worlds = get_available_worlds()
        current_world = session.get('world_path')

        return render_template('world_selector.html',
                             worlds=worlds,
                             current_world=current_world)

    @app.route('/select_world', methods=['POST'])
    def select_world():
        """Select a world and store in session."""
        world_name = request.form.get('world_name')

        if not world_name:
            flash('Please select a world', 'error')
            return redirect(url_for('index'))

        world_path = os.path.join(worlds_dir, world_name)
        db_path = os.path.join(world_path, 'world.db')
        config_path = os.path.join(world_path, 'config.json')

        if not os.path.exists(db_path):
            flash(f'World "{world_name}" not found', 'error')
            return redirect(url_for('index'))

        # Get display name from config
        display_name = world_name
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    display_name = config.get('world_name', world_name)
            except Exception as e:
                logger.warning(f"Failed to read config when selecting world '{world_name}': {e}")

        # Store world in session (both folder name and display name)
        session['world_path'] = world_path
        session['world_name'] = world_name  # Folder name for file operations
        session['world_display_name'] = display_name  # Aesthetic name for UI
        flash(f'Entered realm: {display_name}', 'success')

        # Redirect to client interface
        return redirect(url_for('client.index'))

    @app.route('/switch_world')
    def switch_world():
        """Clear world selection and return to selector."""
        session.pop('world_path', None)
        session.pop('world_name', None)
        session.pop('world_display_name', None)
        flash('Returned to Realm Portal', 'info')
        return redirect(url_for('index'))

    @app.route('/api/available_modules')
    def api_available_modules():
        """JSON API: Get all available modules for world creation."""
        loader = ModuleLoader()
        modules = loader.discover_available_modules()
        return jsonify({'modules': modules})

    @app.route('/api/roll_types')
    def api_roll_types():
        """JSON API: Get all registered roll types."""
        world_path = session.get('world_path')
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
        roll_types = engine.storage.get_roll_types()
        return jsonify({'roll_types': roll_types})

    @app.route('/api/registries')
    def api_registries():
        """JSON API: Get all module registry names."""
        world_path = session.get('world_path')
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
        registry_names = engine.storage.get_registry_names()
        return jsonify({'registries': registry_names})

    @app.route('/api/registries/<registry_name>')
    def api_registry_values(registry_name):
        """JSON API: Get all values from a specific registry."""
        world_path = session.get('world_path')
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
        values = engine.storage.get_registry_values(registry_name)
        return jsonify({
            'registry_name': registry_name,
            'values': values
        })

    @app.route('/create_world', methods=['POST'])
    def create_world():
        """Create a new world with selected modules."""
        try:
            world_name = request.form.get('world_name', '').strip()
            realm_name = request.form.get('realm_name', '').strip()
            selected_modules = request.form.getlist('modules')

            # Validation
            if not world_name:
                flash('Please provide a realm folder name', 'error')
                return redirect(url_for('index'))

            if not realm_name:
                flash('Please provide a realm display name', 'error')
                return redirect(url_for('index'))

            # Sanitize world_name for filesystem
            import re
            world_name = re.sub(r'[^a-zA-Z0-9_-]', '_', world_name)

            world_path = os.path.join(worlds_dir, world_name)

            # Check if world already exists
            if os.path.exists(os.path.join(world_path, 'world.db')):
                flash(f'A realm named "{world_name}" already exists', 'error')
                return redirect(url_for('index'))

            # Ensure core_components is always included
            if not selected_modules:
                selected_modules = ['core_components']
            elif 'core_components' not in selected_modules:
                selected_modules.insert(0, 'core_components')

            # Create the world
            engine = StateEngine.initialize_world(
                world_path=world_path,
                world_name=realm_name,
                modules=selected_modules
            )

            flash(f'Realm "{realm_name}" created successfully with {len(selected_modules)} arcane module(s)', 'success')

            # Auto-select the new world
            session['world_path'] = world_path
            session['world_name'] = world_name
            session['world_display_name'] = realm_name

            return redirect(url_for('client.index'))

        except Exception as e:
            flash(f'Failed to create realm: {str(e)}', 'error')
            return redirect(url_for('index'))

    @app.route('/delete_world', methods=['POST'])
    def delete_world():
        """Delete a world (permanently removes the world directory)."""
        try:
            world_name = request.form.get('world_name', '').strip()

            if not world_name:
                flash('Please specify a world to delete', 'error')
                return redirect(url_for('index'))

            world_path = os.path.join(worlds_dir, world_name)

            # Check if world exists
            if not os.path.exists(world_path):
                flash(f'World "{world_name}" not found', 'error')
                return redirect(url_for('index'))

            # Get world display name from config if possible
            config_path = os.path.join(world_path, 'config.json')
            display_name = world_name
            if os.path.exists(config_path):
                try:
                    import json
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        display_name = config.get('world_name', world_name)
                except Exception as e:
                    logger.warning(f"Failed to read config when deleting world '{world_name}': {e}")

            # If currently selected world is being deleted, clear session
            if session.get('world_path') == world_path:
                session.clear()

            # Delete the world directory
            import shutil
            shutil.rmtree(world_path)

            flash(f'Realm "{display_name}" has been permanently deleted', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            flash(f'Error deleting realm: {str(e)}', 'error')
            return redirect(url_for('index'))

    # ========== API Endpoints ==========

    def get_current_world_path():
        """Get current world path from session or return None."""
        return session.get('world_path')

    @app.route('/api/entities')
    def api_entities():
        """JSON API: List all entities."""
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
        entities = engine.list_entities()
        return jsonify([e.to_dict() for e in entities])

    @app.route('/api/entity/<entity_id>')
    def api_entity(entity_id: str):
        """JSON API: Get entity details."""
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
        entity = engine.get_entity(entity_id)

        if not entity:
            return jsonify({'error': 'Entity not found'}), 404

        components = engine.get_entity_components(entity_id)
        relationships = engine.get_relationships(entity_id)

        return jsonify({
            'entity': entity.to_dict(),
            'components': components,
            'relationships': [r.to_dict() for r in relationships]
        })

    @app.route('/api/events')
    def api_events():
        """JSON API: Get recent events."""
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
        limit = request.args.get('limit', 50, type=int)
        entity_id = request.args.get('entity_id', None)
        event_type = request.args.get('type', None)

        events = engine.get_events(
            entity_id=entity_id,
            event_type=event_type,
            limit=limit
        )

        return jsonify([e.to_dict() for e in events])

    @app.route('/api/types')
    def api_types():
        """JSON API: Get registered types."""
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected'}), 400

        engine = StateEngine(world_path)
        return jsonify({
            'components': engine.storage.get_component_types(),
            'relationships': engine.storage.get_relationship_types(),
            'events': engine.storage.get_event_types()
        })

    @app.route('/api/component_form/<component_type>')
    def api_component_form(component_type: str):
        """JSON API: Get form HTML for a component type."""
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected', 'success': False}), 400

        try:
            from src.web.form_builder import FormBuilder
            engine = StateEngine(world_path)
            form_builder = FormBuilder(engine)

            # Generate form HTML for empty component (for adding new)
            form_html = form_builder.build_form(component_type, {})

            return jsonify({
                'success': True,
                'form_html': str(form_html)
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error generating form: {str(e)}'
            }), 500

    @app.route('/api/roll', methods=['POST'])
    def api_roll():
        """
        JSON API: Execute a dice roll for an entity.

        Request JSON:
            {
                "entity_id": "entity-123",
                "notation": "1d20+5",
                "roll_type": "ability_check",
                "label": "Strength Check",
                "advantage": false,  # optional
                "disadvantage": false  # optional
            }

        Returns:
            {
                "success": true,
                "result": {
                    "total": 18,
                    "breakdown": "1d20: [13] = 13 | modifier: +5 | **Total: 18**",
                    "notation": "1d20+5",
                    "natural_20": false,
                    "natural_1": false,
                    ...
                }
            }
        """
        world_path = get_current_world_path()
        if not world_path:
            return jsonify({'error': 'No world selected', 'success': False}), 400

        try:
            data = request.get_json()

            # Validate required fields
            entity_id = data.get('entity_id')
            notation = data.get('notation')
            roll_type = data.get('roll_type')
            label = data.get('label', '')

            if not entity_id or not notation or not roll_type:
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields: entity_id, notation, roll_type'
                }), 400

            # Get optional advantage/disadvantage
            advantage = data.get('advantage', False)
            disadvantage = data.get('disadvantage', False)

            # Initialize engine and roller
            engine = StateEngine(world_path)
            from src.modules.rng.roller import DiceRoller
            roller = DiceRoller()

            # Execute roll
            roll_result = roller.roll(
                notation=notation,
                advantage=advantage,
                disadvantage=disadvantage,
                metadata={
                    'entity_id': entity_id,
                    'roll_type': roll_type,
                    'label': label
                }
            )

            # Log roll.completed event
            from src.core.models import Event
            engine.event_bus.publish(
                Event.create(
                    event_type='roll.completed',
                    entity_id=entity_id,
                    data={
                        'entity_id': entity_id,
                        'notation': notation,
                        'roll_type': roll_type,
                        'purpose': label,
                        'total': roll_result.total,
                        'breakdown': roll_result.get_breakdown(),
                        'advantage': roll_result.advantage,
                        'disadvantage': roll_result.disadvantage,
                        'natural_20': roll_result.natural_20,
                        'natural_1': roll_result.natural_1,
                        'dice_results': [
                            {
                                'expression': str(dr.expression),
                                'rolls': dr.rolls,
                                'total': dr.total
                            }
                            for dr in roll_result.dice_results
                        ],
                        'modifiers_applied': []  # TODO: Add modifier system
                    }
                )
            )

            # Return result
            return jsonify({
                'success': True,
                'result': roll_result.to_dict()
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/equipment/<entity_id>')
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
            engine = StateEngine(world_path)

            # Get items module and equipment system
            from src.modules.items import ItemsModule
            from src.core.module_loader import ModuleLoader

            # Load modules to get equipment system
            loader = ModuleLoader(world_path)
            modules = loader.load_modules(strategy='config')

            # Find items module
            items_module = None
            for module in modules:
                if module.name == 'items':
                    items_module = module
                    break

            if not items_module:
                return jsonify({
                    'success': False,
                    'error': 'Items module not loaded in this world'
                }), 400

            equipment_system = items_module.get_equipment_system()
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
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/inventory/<entity_id>')
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
            engine = StateEngine(world_path)

            # Get items module and equipment system
            from src.core.module_loader import ModuleLoader

            loader = ModuleLoader(world_path)
            modules = loader.load_modules(strategy='config')

            items_module = None
            for module in modules:
                if module.name == 'items':
                    items_module = module
                    break

            if not items_module:
                return jsonify({
                    'success': False,
                    'error': 'Items module not loaded in this world'
                }), 400

            equipment_system = items_module.get_equipment_system()
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
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/equip', methods=['POST'])
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

            engine = StateEngine(world_path)

            # Get equipment system
            from src.core.module_loader import ModuleLoader

            loader = ModuleLoader(world_path)
            modules = loader.load_modules(strategy='config')

            items_module = None
            for module in modules:
                if module.name == 'items':
                    items_module = module
                    break

            if not items_module:
                return jsonify({
                    'success': False,
                    'error': 'Items module not loaded in this world'
                }), 400

            equipment_system = items_module.get_equipment_system()
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
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/unequip', methods=['POST'])
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

            engine = StateEngine(world_path)

            # Get equipment system
            from src.core.module_loader import ModuleLoader

            loader = ModuleLoader(world_path)
            modules = loader.load_modules(strategy='config')

            items_module = None
            for module in modules:
                if module.name == 'items':
                    items_module = module
                    break

            if not items_module:
                return jsonify({
                    'success': False,
                    'error': 'Items module not loaded in this world'
                }), 400

            equipment_system = items_module.get_equipment_system()
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
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ========== WebSocket Event Handlers ==========

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info(f"Client connected: {request.sid}")
        emit('connection_status', {'status': 'connected', 'message': 'Connected to Arcane Arsenal'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {request.sid}")

    @socketio.on('join_world')
    def handle_join_world(data):
        """Join a world room for receiving updates."""
        world_name = data.get('world_name')
        if world_name:
            join_room(f"world_{world_name}")
            logger.info(f"Client {request.sid} joined world: {world_name}")
            emit('joined_world', {'world': world_name})

    @socketio.on('join_entity')
    def handle_join_entity(data):
        """Join an entity room for receiving entity-specific updates."""
        entity_id = data.get('entity_id')
        if entity_id:
            join_room(f"entity_{entity_id}")
            logger.info(f"Client {request.sid} joined entity: {entity_id}")
            emit('joined_entity', {'entity_id': entity_id})

    @socketio.on('roll_dice')
    def handle_roll_dice(data):
        """
        Handle dice roll request via WebSocket.

        Emits roll results in real-time to all clients watching the entity.
        """
        try:
            entity_id = data.get('entity_id')
            notation = data.get('notation')
            roll_type = data.get('roll_type', 'check')
            purpose = data.get('purpose', '')

            if not entity_id or not notation:
                emit('roll_error', {'error': 'Missing entity_id or notation'})
                return

            # Get world from session
            world_path = session.get('world_path')
            if not world_path:
                emit('roll_error', {'error': 'No world selected'})
                return

            # Get engine (already loads and initializes all modules)
            engine = StateEngine(world_path)

            # Subscribe to roll completion BEFORE publishing request (fix race condition)
            roll_complete_received = []

            def on_roll_complete(event):
                roll_complete_received.append(event)

            engine.event_bus.subscribe('roll.completed', on_roll_complete)

            # Publish roll request event
            engine.event_bus.publish(
                Event.create(
                    event_type='roll.requested',
                    entity_id=entity_id,
                    data={
                        'entity_id': entity_id,
                        'notation': notation,
                        'roll_type': roll_type,
                        'purpose': purpose
                    }
                )
            )

            # Event should be processed synchronously since we're in same thread
            if roll_complete_received:
                result_data = roll_complete_received[0].data
                # Broadcast to all players in the world (everyone should see dice rolls)
                socketio.emit('roll_result', result_data, room=f"world_{session.get('world_name')}")
            else:
                logger.error(f"Roll completed event not received for entity {entity_id}")
                emit('roll_error', {'error': 'Roll processing failed'})

        except Exception as e:
            logger.error(f"Dice roll error: {e}", exc_info=True)
            emit('roll_error', {'error': str(e)})

    @socketio.on('update_hp')
    def handle_update_hp(data):
        """
        Handle HP update request via WebSocket.

        Updates entity health and broadcasts to all watchers.
        """
        try:
            entity_id = data.get('entity_id')
            current_hp = data.get('current_hp')
            max_hp = data.get('max_hp')
            temp_hp = data.get('temp_hp', 0)

            if entity_id is None or current_hp is None or max_hp is None:
                emit('hp_error', {'error': 'Missing required HP data'})
                return

            # Get world from session
            world_path = session.get('world_path')
            if not world_path:
                emit('hp_error', {'error': 'No world selected'})
                return

            # Get engine (already loads and initializes all modules)
            engine = StateEngine(world_path)

            # Update health component
            result = engine.update_component(entity_id, 'health', {
                'current_hp': current_hp,
                'max_hp': max_hp,
                'temp_hp': temp_hp
            })

            if result.success:
                # Broadcast HP update to all watchers
                hp_data = {
                    'entity_id': entity_id,
                    'current_hp': current_hp,
                    'max_hp': max_hp,
                    'temp_hp': temp_hp
                }

                # Emit to entity room and world room
                socketio.emit('hp_updated', hp_data, room=f"entity_{entity_id}")
                socketio.emit('hp_updated', hp_data, room=f"world_{session.get('world_name')}")

                emit('hp_update_success', hp_data)
            else:
                emit('hp_error', {'error': result.error})

        except Exception as e:
            logger.error(f"HP update error: {e}", exc_info=True)
            emit('hp_error', {'error': str(e)})

    @socketio.on('broadcast_event')
    def handle_broadcast_event(data):
        """
        Broadcast a game event to all clients in the world.

        Used by DM to send notifications, announcements, etc.
        """
        try:
            world_name = session.get('world_name')
            if not world_name:
                emit('error', {'error': 'No world selected'})
                return

            event_type = data.get('event_type', 'notification')
            message = data.get('message', '')
            event_data = data.get('data', {})

            # Broadcast to all clients in the world
            socketio.emit('game_event', {
                'event_type': event_type,
                'message': message,
                'data': event_data,
                'timestamp': Event.create(event_type=event_type).timestamp
            }, room=f"world_{world_name}")

            emit('broadcast_success', {'message': 'Event broadcasted'})

        except Exception as e:
            logger.error(f"Broadcast error: {e}", exc_info=True)
            emit('error', {'error': str(e)})

    return app, socketio


def main():
    """Run development server."""
    import argparse

    parser = argparse.ArgumentParser(description='Arcane Arsenal Web Interface')
    parser.add_argument('--worlds-dir', default='worlds', help='Directory containing worlds (default: worlds)')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    # Create worlds directory if it doesn't exist
    if not os.path.exists(args.worlds_dir):
        os.makedirs(args.worlds_dir)
        print(f"Created worlds directory: {args.worlds_dir}")

    app, socketio = create_app(args.worlds_dir)

    print(f"\n╔══════════════════════════════════════════════════╗")
    print(f"║     Arcane Arsenal Web Interface                 ║")
    print(f"║     Real-time WebSocket Support Enabled          ║")
    print(f"╚══════════════════════════════════════════════════╝")
    print(f"")
    print(f"  Worlds directory: {args.worlds_dir}")
    print(f"  Server URL:       http://{args.host}:{args.port}")
    print(f"  WebSocket:        Enabled (eventlet)")
    print(f"")
    print(f"  Features:")
    print(f"   • Real-time dice rolls")
    print(f"   • Live HP synchronization")
    print(f"   • Instant DM notifications")
    print(f"")
    print(f"  1. Open http://{args.host}:{args.port} in your browser")
    print(f"  2. Select a world from the list")
    print(f"  3. Start playing!")
    print(f"")
    print(f"  Press Ctrl+C to stop")
    print(f"")

    # Use socketio.run() instead of app.run() for WebSocket support
    socketio.run(app, host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
