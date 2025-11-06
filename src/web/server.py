"""
Web interface for Arcane Arsenal.

Flask app with separate client (player) and host (DM) interfaces.
- /: World selector landing page
- /client: Player interface for character management
- /host: DM interface for full state management
"""

from flask import Flask, jsonify, request, redirect, url_for, session, render_template, flash
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.state_engine import StateEngine
from src.core.module_loader import ModuleLoader
from src.web.blueprints import client_bp, host_bp


def create_app(worlds_dir: str = 'worlds') -> Flask:
    """
    Create Flask app with world selection support.

    Args:
        worlds_dir: Directory containing world folders (default: 'worlds')

    Returns:
        Configured Flask app with client and host blueprints
    """
    app = Flask(__name__)
    app.config['WORLDS_DIR'] = worlds_dir
    app.config['SECRET_KEY'] = os.urandom(24)  # For sessions and flash messages

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
                    except:
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
            except:
                pass

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
                except:
                    pass

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

    return app


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

    app = create_app(args.worlds_dir)

    print(f"\n╔══════════════════════════════════════════════════╗")
    print(f"║     Arcane Arsenal Web Interface                 ║")
    print(f"╚══════════════════════════════════════════════════╝")
    print(f"")
    print(f"  Worlds directory: {args.worlds_dir}")
    print(f"  Server URL:       http://{args.host}:{args.port}")
    print(f"")
    print(f"  1. Open http://{args.host}:{args.port} in your browser")
    print(f"  2. Select a world from the list")
    print(f"  3. Start playing!")
    print(f"")
    print(f"  Press Ctrl+C to stop")
    print(f"")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
