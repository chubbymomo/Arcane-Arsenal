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

    # Initialize StateEngine instance cache
    # Each world gets one StateEngine that persists for the app lifetime
    # This avoids creating new database connections on every request
    app.engine_instances = {}

    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",  # Configure appropriately for production
        async_mode='eventlet',
        logger=True,
        engineio_logger=False
    )

    # Custom Jinja2 filters
    @app.template_filter('component_name')
    def format_component_name(name):
        """Format component type names for display (e.g., 'RollHistory' -> 'Roll History')."""
        import re
        # Handle special cases first
        if name == 'RollHistory':
            return '🎲 Roll History'
        elif name == 'InventoryDisplay':
            return '🎒 Inventory & Equipment'
        # Split on capital letters and join with spaces
        formatted = re.sub(r'(?<!^)(?=[A-Z])', ' ', name)
        return formatted

    # Register core blueprints
    app.register_blueprint(client_bp)
    app.register_blueprint(host_bp)

    # Auto-discover and register module blueprints
    # This allows modules to provide their own API endpoints without modifying core
    try:
        loader = ModuleLoader()
        available_modules = loader.discover_available_modules()

        for module_info in available_modules:
            try:
                # Load the module instance
                module_instance = loader.load_module(module_info['name'])

                if module_instance is None:
                    continue

                # Check if module provides a blueprint
                blueprint = module_instance.register_blueprint()

                if blueprint is not None:
                    app.register_blueprint(blueprint)
                    logger.info(f"Registered blueprint from module: {module_info['name']}")
            except Exception as e:
                # Don't fail server startup if a module blueprint fails to load
                logger.warning(f"Failed to register blueprint from module '{module_info['name']}': {e}")
    except Exception as e:
        logger.warning(f"Failed to auto-discover module blueprints: {e}")

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

        # Initialize StateEngine for this world if not already cached
        if world_name not in app.engine_instances:
            logger.info(f"Initializing StateEngine for world: {world_name}")
            engine = StateEngine(world_path)

            # Load and initialize modules for this world
            logger.info(f"Loading modules for world: {world_name}")
            loader = ModuleLoader(world_path)
            modules = loader.load_modules(strategy='config')

            for module in modules:
                try:
                    module.initialize(engine)
                    logger.info(f"  ✓ Initialized module: {module.name}")
                except Exception as e:
                    logger.warning(f"  ✗ Failed to initialize module {module.name}: {e}")

            # Cache the fully initialized engine
            app.engine_instances[world_name] = engine
            logger.info(f"✓ StateEngine initialized and cached for: {world_name} with {len(modules)} modules")

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
        try:
            engine = get_engine()
            roll_types = engine.storage.get_roll_types()
            return jsonify({'roll_types': roll_types})
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/registries')
    def api_registries():
        """JSON API: Get all module registry names."""
        try:
            engine = get_engine()
            registry_names = engine.storage.get_registry_names()
            return jsonify({'registries': registry_names})
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/registries/<registry_name>')
    def api_registry_values(registry_name):
        """JSON API: Get all values from a specific registry."""
        try:
            engine = get_engine()
            values = engine.storage.get_registry_values(registry_name)
            return jsonify({
                'registry_name': registry_name,
                'values': values
            })
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

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

    def get_engine():
        """Get the cached StateEngine for the current world."""
        world_name = session.get('world_name')
        if not world_name:
            raise ValueError('No world selected')

        engine = app.engine_instances.get(world_name)
        if not engine:
            raise ValueError(f'StateEngine not initialized for world: {world_name}')

        return engine

    @app.route('/api/entities')
    def api_entities():
        """JSON API: List all entities."""
        try:
            engine = get_engine()
            entities = engine.list_entities()
            return jsonify([e.to_dict() for e in entities])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/entity/<entity_id>')
    def api_entity(entity_id: str):
        """JSON API: Get entity details."""
        try:
            engine = get_engine()
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
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/events')
    def api_events():
        """JSON API: Get recent events."""
        try:
            engine = get_engine()
            limit = request.args.get('limit', 50, type=int)
            entity_id = request.args.get('entity_id', None)
            event_type = request.args.get('type', None)

            events = engine.get_events(
                entity_id=entity_id,
                event_type=event_type,
                limit=limit
            )

            return jsonify([e.to_dict() for e in events])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/types')
    def api_types():
        """JSON API: Get registered types."""
        try:
            engine = get_engine()
            return jsonify({
                'components': engine.storage.get_component_types(),
                'relationships': engine.storage.get_relationship_types(),
                'events': engine.storage.get_event_types()
            })
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/component_form/<component_type>')
    def api_component_form(component_type: str):
        """JSON API: Get form HTML for a component type."""
        try:
            from src.web.form_builder import FormBuilder
            engine = get_engine()
            form_builder = FormBuilder(engine)

            # Generate form HTML for empty component (for adding new)
            form_html = form_builder.build_form(component_type, {})

            return jsonify({
                'success': True,
                'form_html': str(form_html)
            })
        except ValueError as e:
            return jsonify({'error': str(e), 'success': False}), 400
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
        try:
            engine = get_engine()
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

            # Initialize roller
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

            # Get engine (cached, already initialized with modules)
            try:
                engine = get_engine()
            except ValueError as e:
                emit('roll_error', {'error': str(e)})
                return

            # Subscribe to roll completion BEFORE publishing request (fix race condition)
            roll_complete_received = []

            def on_roll_complete(event):
                roll_complete_received.append(event)

            engine.event_bus.subscribe('roll.completed', on_roll_complete)

            # Publish roll request event
            engine.event_bus.publish(
                Event.create(
                    event_type='roll.initiated',
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

                # Add entity name for display in roll history
                entity = engine.get_entity(entity_id)
                if entity:
                    result_data['entity_name'] = entity.name
                else:
                    result_data['entity_name'] = 'Unknown'

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

            # Get engine (cached, already initialized with modules)
            try:
                engine = get_engine()
            except ValueError as e:
                emit('hp_error', {'error': str(e)})
                return

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
